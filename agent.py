from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import tool
from langsmith import traceable
from langchain_community.tools.shell.tool import ShellTool
from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
import subprocess
from dotenv import load_dotenv
from langchain.globals import set_llm_cache
from langchain_community.cache import SQLiteCache
from typing import Optional
from pathlib import Path
import os

load_dotenv()
set_llm_cache(SQLiteCache(database_path=".langchain.db"))

ROOT_DIR = "."
REPO_DIR = "cloudfix-aws"
VALID_FILE_TYPES = {"py", "txt", "md", "cpp", "c", "java", "js", "html", "css", "ts", "json"}

yarn_path = r"C:\Program Files\nodejs\yarn.cmd"
npm_path = r"C:\Program Files\nodejs\npm.cmd"

@tool
def create_directory(directory: str) -> str:
    """
    Creates a new writable directory with the given name if it does not exist.
    Returns Success or error message.
    """
    try:
        path = Path(ROOT_DIR).joinpath(directory)
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(0o755)
        return f"Successfully created directory {directory}"
    except Exception as e:
        return f"Failed to create directory {directory}: {str(e)}"

@tool
def find_file(filename: str, path: str) -> Optional[str]:
    """
    Recursively searches for a file in the given path.
    Returns the path of the file if found, otherwise returns None.
    """
    path_obj = Path(path)
    for file in path_obj.rglob(filename):
        return str(file)
    return None



@tool
def create_file(filename: str, content: str = "", directory=""):
    """
    Creates a new file and content in the specified directory. 
    Creates the directory if it doesn't exist.
    Filetype must be in {"py", "txt", "md", "cpp", "c", "java", "js", "html", "css", "ts", "json"}
    """
    # Validate file type
    try:
        file_stem, file_type = filename.split(".")
        assert file_type in VALID_FILE_TYPES
    except:
        return f"Invalid filename {filename} - must end with a valid file type: {VALID_FILE_TYPES}"
    
    create_directory(directory)
    file_path = Path(ROOT_DIR).joinpath(directory).joinpath(filename)
    if not file_path.exists():
        try:
            with file_path.open("w") as file:
                file.write(content)
            return f"Successfully created file {filename} at {file_path}"
        except Exception as e:
            return f"Failed to create file {filename} at {file_path}: {str(e)}"
    else:
        return f"File {filename} already exists at {file_path}."
    

@tool
def open_file(filename: str, directory: str = ROOT_DIR):
    """Opens an existing file."""
    file_path = Path(ROOT_DIR).joinpath(directory).joinpath(filename)
    if not file_path.exists():
        return f"File {filename} not found in {directory}."
    else:
        try:
            with open(file_path, "r") as file:
                return file.read()    
        except Exception as e:
            return f"Failed to open file {filename} at {file_path}: {str(e)}"

@tool
def replace_file(filename: str, content: str, directory: str = ROOT_DIR):
    """Updates an existing file by completely replacing its content."""
    file_path = Path(ROOT_DIR).joinpath(directory).joinpath(filename)
    if not file_path.exists():
        return f"File {filename} not found in {directory}."
    else:
        try:
            with open(file_path, "w") as file:
                file.write(content)
            return f"Successfully updated file {filename} at {file_path}"
        except Exception as e:
            return f"Failed to update file {filename} at {file_path}: {str(e)}"
        
@tool
def append_file(filename: str, content: str, directory: str = ROOT_DIR):
    """Appends content to an existing file at the end."""
    file_path = Path(ROOT_DIR).joinpath(directory).joinpath(filename)
    if not file_path.exists():
        return f"File {filename} not found in {directory}."
    else:
        try:
            with open(file_path, "a") as file:
                file.write(content)
            return f"Successfully appended content to file {filename} at {file_path}"
        except Exception as e:
            return f"Failed to append content to file {filename} at {file_path}: {str(e)}"

# AI-GEN START - cursor
@tool
def edit_lines(filename: str, start_line: int, end_line: int, new_content: str, directory: str = ROOT_DIR) -> str:
    """
    Replaces lines in an existing file between start_line and end_line (inclusive) with new_content. The line numbers start with 1.    
    Returns a message indicating success or failure.
    """
    file_path = Path(ROOT_DIR).joinpath(directory).joinpath(filename)
    if not file_path.exists():
        return f"File {filename} not found in {directory}."
    
    try:
        with open(file_path, "r") as file:
            lines = file.readlines()
        
        if start_line < 1 or end_line > len(lines) or start_line > end_line:
            return f"Invalid line range specified for file {filename}."
        
        # Replace the specified lines with new content
        lines[start_line-1:end_line] = [new_content + "\n"]
        
        with open(file_path, "w") as file:
            file.writelines(lines)
        
        return f"Successfully edited lines {start_line} to {end_line} in file {file_path}"
    except Exception as e:
        return f"Failed to edit file {file_path}: {str(e)}"
# AI-GEN END


@tool
def ls(directory: str = ROOT_DIR) -> dict:
    """
    Lists the files and directories in the given directory.
    Returns:
        dict:  with keys "current_directory", "files", "directories"
    """
    if not os.path.exists(directory):
        return f"Directory {directory} not found."
    
    try:
        files_and_dirs = os.listdir(directory)
        return {
            "current_directory": directory,            
            "files": [f for f in files_and_dirs if os.path.isfile(os.path.join(directory, f))],
            "directories": [d for d in files_and_dirs if os.path.isdir(os.path.join(directory, d))]
        }
    except Exception as e:
        return f"Failed to list directory contents: {str(e)}"

@tool
def compile():
    """
    Compiles the project return Success or compilation error message.
    """
    try:
        result = subprocess.run(["yarn", "install"], capture_output=True, text=True, cwd=REPO_DIR)
        if result.returncode != 0:
            return f"Failed to install frozen lockfile: {result.stderr}"
        result = subprocess.run(["npm", "run", "analyze-code"], capture_output=True, text=True, cwd=REPO_DIR)
        if result.returncode == 0:
            return f"Compilation successful"
        else:
            return f"Compilation failed: {result.stdout} {result.stderr}"
    except Exception as e:
        return f"Failed to run compile command: {str(e)}"
    
@tool
def lint() -> str:
    """
    Runs the linting process on the project with fixing enabled. 
    
    Returns:
        str: Result message indicating success or failure.
    """
    try:
        result = subprocess.run(["npm", "run", "lint"], capture_output=True, text=True, cwd=REPO_DIR)
        if result.returncode == 0:
            return f"Linting successful"
        else:
            return f"Linting failed: {result.stderr}"
    except Exception as e:
        return f"Failed to run lint command: {str(e)}"
    
@tool
def create_and_push_branch(branch_name: str, commit_message: str) -> str:
    """
    Creates a new branch and adds all the changes to it.
    
    Args:
        branch_name (str): The name of the new branch to create and push.
        commit_message (str): The commit message to use for the changes.
    
    Returns:
        str: Result message indicating success or failure.
    """
    try:
        # Create a new branch
        result = subprocess.run(["git", "checkout", "-b", branch_name], capture_output=True, text=True, cwd=REPO_DIR)
        if result.returncode != 0:
            return f"Failed to create branch: {result.stderr}"
        
        # Add all changes
        result = subprocess.run(["git", "add", "."], capture_output=True, text=True, cwd=REPO_DIR)
        if result.returncode != 0:
            return f"Failed to add changes: {result.stderr}"
        
        # Commit the changes
        result = subprocess.run(["git", "commit", "-nm", commit_message], capture_output=True, text=True, cwd=REPO_DIR)
        if result.returncode != 0:
            return f"Failed to commit changes: {result.stderr}"
     
        # Push the changes to the remote repository
        result = subprocess.run(["git", "push", "--set-upstream", "origin", branch_name], capture_output=True, text=True, cwd=REPO_DIR)
        if result.returncode != 0:
            return f"Failed to push branch: {result.stderr}"
             
        return f"Successfully created and pushed branch {branch_name}"
    except Exception as e:
        return f"Failed to create and push branch: {str(e)}"

@tool
def git_diff() -> str:
    """
    Shows the changes made so far.
    Returns:
        str: The git diff output or an error message.
    """
    try:
        result = subprocess.run(["git", "diff"], capture_output=True, text=True, cwd=REPO_DIR)
        if result.returncode == 0:
            return result.stdout
        else:
            return f"Failed to get git diff: {result.stderr}"
    except Exception as e:
        return f"Failed to run git diff command: {str(e)}"

# AI-GEN START - cursor
@tool
def git_reset() -> str:
    """
    Resets the current Git repository to the last commit. Use this if you want to start from scratch.
    
    Returns:
        str: Result message indicating success or failure.
    """
    try:
        result = subprocess.run(["git", "reset", "--hard"], capture_output=True, text=True, cwd=REPO_DIR)
        if result.returncode == 0:
            return "Successfully reset the repository to the last commit."
        else:
            return f"Failed to reset the repository: {result.stderr}"
    except Exception as e:
        return f"Failed to run git reset command: {str(e)}"
# AI-GEN END



# List of tools to use
tools = [
    ShellTool(ask_human_input=True), 
    create_directory, 
    open_file,
    find_file, 
    create_file, 
    append_file,
    replace_file,
    edit_lines,
    ls,
    compile,
    lint,
    create_and_push_branch,
    git_diff
]

# Configure the language model
llm = ChatOpenAI(model="gpt-4o", temperature=0, max_tokens=4000, max_retries=5)

# Set up the prompt template
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are an expert TypeScript developer working on the cloudfix-aws project. This project contains a tree structure of directories and files for various finders, located in the cloudfix-aws/cloudfix-ff/src/ff directory. Each finder has a ValidatorService.ts file that contains the validation logic.
You don't have to describe the modifications being made use the provided tools to make the changes. When editing lines prefer to edit block of code in a single request.
If there you face many errors use reset tool to start from scratch.
We need to enhance the validation logic to include a customer-facing report about the recommendation. Make sure you only make limited changes to the code, focus only on the report implementation.
To achieve this, follow these steps:

Review the existing report implementations:
\"\"\"
export const ReportTemplate = `# EBS Volume Cleanup - Long Stopped Volume

Cloudfix identified an opportunity to clean up an EBS volume that has been stopped/detached from any active instance for over {{IdleDays}} consecutive days, resulting in unused storage allocation charges.

Deleting this long-stopped volume could yield monthly savings.

## Stopped Volume Details

* **Volume ID:** {{VolumeId}}
* **Instance ID:** {{InstanceId}}
* **Volume Type:** {{VolumeType}}
* **Storage Allocated:** {{VolumeSize}}GB
* **Instance stopped since at least:** {{StoppedDate}}
* **Annual Cost Savings:** {{formatMoney AnnualCost}}

## Recommendation

We recommended deleting the EBS volume if it is no longer needed. This action will remove the volume and free up storage, saving costs. Before deletion, CloudFix will create a snapshot.

For more detailed instructions and best practices, please refer to the CloudFix support article: [Delete EBS volumes attached to long-stopped EC2 instances](https://support.cloudfix.com/hc/en-us/articles/10398173847698-Delete-EBS-volumes-attached-to-long-stopped-EC2-instances).`;
\"\"\"
\"\"\"
export const ReportTemplate = `# GP2 to GP3 Volume Upgrade 

Cloudfix identified an opportunity to upgrade your {{VolumeId}} EBS volume from a GP2 configuration to the latest General Purpose SSD (GP3) offering. Upgrading this volume could realize significant cost savings while still meeting performance needs.

## Configuration Comparison

| Configuration     | Current (GP2) | Target (GP3) |
|-------------------|---------------|--------------|
| **Volume ID**     | {{VolumeId}}  | {{VolumeId}} |
| **Allocated Size**| {{VolumeSize}} GB | {{VolumeSize}} GB |
| **IOPS** | {{gp2Iops}}  | {{gp3Iops}} (3000 baseline + {{provisionedIops}} provisioned) |
| **Throughput**  [MB/s] | {{gp2Throughput}}  | {{gp3Throughput}} (125 baseline + {{provisionedThroughput}} provisioned) |
| **Cost**    | {{formatMoney gp2Cost}} | {{formatMoney gp3Cost}} |

This shows that the new volume performs at least the same as the current volume.

## Recommendation

The recommended GP3 configuration would provide {{gp3Iops}} IOPS and up to {{gp3Throughput}} MB/s throughput while **reducing your yearly cost by {{formatMoney AnnualSavings}}** over current GP2 usage.

Upgrade volume {{VolumeId}} to GP3 type to realize these savings.

For more details on EBS volume cost optimizations from GP2 to GP3, please visit our [support article](https://support.cloudfix.com/hc/en-us/articles/6042981066642-EBS-Volume-Cost-Optimizations-GP2-to-GP3)`;
\"\"\"
\"\"\"
# ECS Optimization

Cloudfix identified an opportunity to optimize your ECS tasks and clusters to improve cost efficiency and performance.

## Configuration Comparison

| Configuration     | Current | Optimized |
|-------------------|---------|-----------|
| **Cluster ID**    | {{ClusterId}} | {{ClusterId}} |
| **Task ARN**      | {{TaskArn}} | {{TaskArn}} |
| **CPU Usage**     | {{CurrentCpuUsage}} vCPUs | {{OptimizedCpuUsage}} vCPUs |
| **Memory Usage**  | {{CurrentMemoryUsage}} MB | {{OptimizedMemoryUsage}} MB |
| **Cost**          | {{formatMoney CurrentCost}} | {{formatMoney OptimizedCost}} |

This table shows that the optimized configuration will provide the same or better performance at a lower cost.

## Recommendation

The recommended optimization would adjust the CPU and memory usage of your ECS tasks, **reducing your yearly cost by {{formatMoney AnnualSavings}}**.

Optimize your ECS tasks and clusters to realize these savings.

For more details on ECS optimization, please visit our [support article](https://support.cloudfix.com/hc/en-us/articles/1400326972898-ECS-EC2-Manual-Retyping)`;
\"\"\"
\"\"\"
# ECS Optimization

Cloudfix identified an opportunity to optimize your ECS tasks and clusters to improve cost efficiency and performance.

## Configuration Comparison

| Configuration     | Current | Optimized |
|-------------------|---------|-----------|
| **Cluster ID**    | {{ClusterId}} | {{ClusterId}} |
| **Task ARN**      | {{TaskArn}} | {{TaskArn}} |
| **CPU Usage**     | {{CurrentCpuUsage}} vCPUs | {{OptimizedCpuUsage}} vCPUs |
| **Memory Usage**  | {{CurrentMemoryUsage}} MB | {{OptimizedMemoryUsage}} MB |
| **Cost**          | {{formatMoney CurrentCost}} | {{formatMoney OptimizedCost}} |

This table shows that the optimized configuration will provide the same or better performance at a lower cost.

## Recommendation

The recommended optimization would adjust the CPU and memory usage of your ECS tasks, **reducing your yearly cost by {{formatMoney AnnualSavings}}**.

Optimize your ECS tasks and clusters to realize these savings.

For more details on ECS optimization, please visit our [support article](https://support.cloudfix.com/hc/en-us/articles/1400326972898-ECS-EC2-Manual-Retyping)`;
\"\"\"
\"\"\"
# S3 Intelligent Tiering Optimization

Cloudfix identified an opportunity to optimize your S3 bucket storage costs and performance using S3 Intelligent Tiering based on access patterns analysis.

## Bucket Impacted

The bucket {{BucketName}} is currently utilizing a mix of storage classes. Implementing S3 Intelligent Tiering could enhance cost-efficiency and performance without compromising on accessibility.

## Recommendation

Enabling S3 Intelligent Tiering can dynamically adjust storage classes to match usage patterns, potentially leading to significant savings. It automatically moves data to the most cost-effective access tier without service disruption.
For more details on S3 Intelligent Tiering, refer to our [support article](https://support.cloudfix.com/hc/en-us/articles/6040475998610-Cost-Optimization-with-AWS-S3-Intelligent-Tiering).
\"\"\"

Review the existing report implementations:
 - template - cloudfix-aws/cloudfix-ff/src/ff/Ebs/Retype/Gp2Volumes/Main.ts variable ReportTemplate
 - validator - cloudfix-aws/cloudfix-ff/src/ff/Ebs/Retype/Gp2Volumes/finder/ValidatorService.ts variable item.finderReportData

New template preparation:
 - analyze the previous implementations
 - inspect the validator to understand the validations performed and data gathered
 - create a handlebars template for the report and place the template in the Main.ts file of the respective finder folder
 - update the ValidatorService.ts to include a finderReportData field for every recommendation. 
 - make sure the finderReportData is populated with the necessary values for the Handlebars template.

Final Steps:
Review the modified the files and ensure that the implementation is complete and error-free.
Compile the project and fix any issues that arise.
Lint the project to ensure that the implementation is compliant with the linting rules.
You use several attempt to make sure that the code is compliant, but no more than 10. If that fails, just submit the prepared code.
Create a new branch and add all the changes to it.
            """,
        ),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

# Bind the tools to the language model
llm_with_tools = llm.bind_tools(tools)

# Create the agent
agent = (
    {
        "input": lambda x: x["input"],
        "agent_scratchpad": lambda x: format_to_openai_tool_messages(
            x["intermediate_steps"]
        ),
    }
    | prompt
    | llm_with_tools
    | OpenAIToolsAgentOutputParser()
)

# Create the agent executor
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False, handle_parsing_errors=True, max_iterations=50)

# Main loop to prompt the user

user_prompt = """
Your task is to implement the report for the finder located in cloudfix-aws/cloudfix-ff/src/ff/Ebs/Delete/IdleVolumes.
"""
finders = [
    "cloudfix-aws/cloudfix-ff/src/ff/Emr/Enable/ManagedScaling",
    "cloudfix-aws/cloudfix-ff/src/ff/Emr/Optimize/Instances",
    "cloudfix-aws/cloudfix-ff/src/ff/Emr/Reserve/Instances",
    "cloudfix-aws/cloudfix-ff/src/ff/Emr/Consolidate/AzInstances",
    "cloudfix-aws/cloudfix-ff/src/ff/Emr/Retype/Tasks",
    "cloudfix-aws/cloudfix-ff/src/ff/Emr/Delete/IdleClusters",
    "cloudfix-aws/cloudfix-ff/src/ff/Rds/Optimize/Instances",
    "cloudfix-aws/cloudfix-ff/src/ff/Rds/Optimize/ProvisionedIops",
    "cloudfix-aws/cloudfix-ff/src/ff/Rds/Optimize/EOLVersion",
    "cloudfix-aws/cloudfix-ff/src/ff/Rds/Scan/ReserveInstances",
    "cloudfix-aws/cloudfix-ff/src/ff/Rds/Resize/Storage",
    "cloudfix-aws/cloudfix-ff/src/ff/Rds/Resize/PostgresClusters",
    "cloudfix-aws/cloudfix-ff/src/ff/Rds/Resize/AuroraMySQLClusters",
    "cloudfix-aws/cloudfix-ff/src/ff/Rds/Retype/Instances",
    "cloudfix-aws/cloudfix-ff/src/ff/Rds/Retype/IoOptimized",
    "cloudfix-aws/cloudfix-ff/src/ff/Rds/Retype/AuroraToGraviton",
    "cloudfix-aws/cloudfix-ff/src/ff/Rds/Retype/AuroraServerless",
    "cloudfix-aws/cloudfix-ff/src/ff/Rds/Retype/SingleAZ",
    "cloudfix-aws/cloudfix-ff/src/ff/Rds/Delete/IdleClusters",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/Enable/ComputeOptimizer",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/Optimize/Asg",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/Optimize/Ecs",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/Optimize/Instances",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/Optimize/MsSqlLicenses",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/Optimize/Gpu",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/Optimize/Eks",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/FixConfiguration/VpcDns",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/FixConfiguration/InstanceProfiles",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/FixConfiguration/CloudWatchAgents",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/FixConfiguration/SsmAgents",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/FixConfiguration/VpcEndpoints",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/Install/CloudWatchAgents",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/Install/SsmAgents",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/Install/SsmAgentsViaInstanceConnect",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/Resize/Asg",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/Resize/Instances",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/Retype/InstancesIntelToAmd",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/Retype/EcsFargateTasks",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/Delete/IdleInstances",
    "cloudfix-aws/cloudfix-ff/src/ff/Ec2/Delete/IdleAMIs",
    "cloudfix-aws/cloudfix-ff/src/ff/ElastiCache/Delete/IdleClusters",
    "cloudfix-aws/cloudfix-ff/src/ff/CloudFront/Enable/Compression",
    "cloudfix-aws/cloudfix-ff/src/ff/ML/Stop/IdleSagemakerNotebooks",
    "cloudfix-aws/cloudfix-ff/src/ff/ML/Resize/Sagemaker",
    "cloudfix-aws/cloudfix-ff/src/ff/ML/Retype/ToInferentia",
    "cloudfix-aws/cloudfix-ff/src/ff/ML/Delete/IdleSagemakerModels",
    "cloudfix-aws/cloudfix-ff/src/ff/ML/Delete/IdleEndpoints",
    "cloudfix-aws/cloudfix-ff/src/ff/ML/Delete/IdleBedrockModels",
    "cloudfix-aws/cloudfix-ff/src/ff/DatabaseMigrationService/Delete/IdleInstances",
    "cloudfix-aws/cloudfix-ff/src/ff/Efs/Enable/IntelligentTiering",
    "cloudfix-aws/cloudfix-ff/src/ff/OpenSearch/Resize/Instances",
    "cloudfix-aws/cloudfix-ff/src/ff/OpenSearch/Resize/Volumes",
    "cloudfix-aws/cloudfix-ff/src/ff/OpenSearch/Retype/InstancesToGraviton",
    "cloudfix-aws/cloudfix-ff/src/ff/AWS/Scan/Cost",
    "cloudfix-aws/cloudfix-ff/src/ff/Ebs/Archive/OldVolumeSnapshots",
    "cloudfix-aws/cloudfix-ff/src/ff/Ebs/Retype/Io1Io2Volumes",
    "cloudfix-aws/cloudfix-ff/src/ff/Ebs/Retype/Gp2Volumes",
    "cloudfix-aws/cloudfix-ff/src/ff/Ebs/Delete/LongStoppedVolumes",
    "cloudfix-aws/cloudfix-ff/src/ff/Ebs/Delete/IdleVolumes",
    "cloudfix-aws/cloudfix-ff/src/ff/Neptune/Delete/IdleClusters",
    "cloudfix-aws/cloudfix-ff/src/ff/CloudTrail/Delete/DuplicateTrail",
    "cloudfix-aws/cloudfix-ff/src/ff/DynamoDb/Retype/Table",
    "cloudfix-aws/cloudfix-ff/src/ff/Eks/Optimize/EOLVersion",
    "cloudfix-aws/cloudfix-ff/src/ff/S3/Enable/IntelligentTiering",
    "cloudfix-aws/cloudfix-ff/src/ff/S3/Enable/DDBTrafficRedirect",
    "cloudfix-aws/cloudfix-ff/src/ff/Bedrock/Delete/IdleKBs",
    "cloudfix-aws/cloudfix-ff/src/ff/Elb/Delete/IdleLoadBalancers",
    "cloudfix-aws/cloudfix-ff/src/ff/Vpc/Consolidate/EndpointsESW",
    "cloudfix-aws/cloudfix-ff/src/ff/Vpc/Delete/IdleEndpoints",
    "cloudfix-aws/cloudfix-ff/src/ff/Vpc/Delete/IdleElasticIPAddresses",
    "cloudfix-aws/cloudfix-ff/src/ff/Vpc/Delete/IdleNATGateways",
    "cloudfix-aws/cloudfix-ff/src/ff/QuickSight/Delete/IdleUsers",
    "cloudfix-aws/cloudfix-ff/src/ff/Kendra/Delete/IdleIndices"
]

for finder in finders:
    retry_attempts = 5
    for attempt in range(5):
        print(f"{finder} - attempt {attempt + 1} of 5")
        subprocess.run(["git", "reset", "--hard"], check=True, cwd=REPO_DIR)
        subprocess.run(["git", "checkout", "qa"], check=True, cwd=REPO_DIR)
        subprocess.run(["git", "reset", "--hard"], check=True, cwd=REPO_DIR)
        subprocess.run(["git", "clean", "-fd"], check=True, cwd=REPO_DIR)
        try:
            list(agent_executor.stream({"input": "Your task is to implement the report for the finder located in "+finder}))
            break
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}");
            # AI-GEN START - cursor
        branch_name = f"{finder.replace('/', '_')}_attempt_{attempt + 1}"
        create_and_push_branch.func(branch_name,"Partial implementation for "+finder)

