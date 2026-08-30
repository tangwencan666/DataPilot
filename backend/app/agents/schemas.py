from datetime import datetime
from enum import Enum
from typing import Annotated,Any,Literal,Union
from pydantic import BaseModel,ConfigDict,Field,field_validator
from app.analysis.schemas import AnalysisPlan
from app.charts.schemas import ChartSpec
from app.models import AgentRunStatus,AgentStepStatus

class ToolName(str,Enum):SQL="SQL";ANALYSIS="ANALYSIS";CHART="CHART"
class StrictModel(BaseModel):model_config=ConfigDict(extra="forbid")
class DatasetSource(StrictModel):type:Literal["dataset"]="dataset"
class SQLStepInput(StrictModel):source:DatasetSource=Field(default_factory=DatasetSource);question:str=Field(min_length=1,max_length=2000)
class AnalysisStepInput(StrictModel):source:DatasetSource=Field(default_factory=DatasetSource);plan:AnalysisPlan
class ChartStepInput(StrictModel):source:DatasetSource=Field(default_factory=DatasetSource);spec:ChartSpec

class SQLAgentStep(StrictModel):
    id:str=Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$");tool:Literal["SQL"];purpose:str=Field(min_length=1,max_length=500);depends_on:list[str]=Field(default_factory=list,max_length=8);input:SQLStepInput;expected_output:str=Field(min_length=1,max_length=500)
class AnalysisAgentStep(StrictModel):
    id:str=Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$");tool:Literal["ANALYSIS"];purpose:str=Field(min_length=1,max_length=500);depends_on:list[str]=Field(default_factory=list,max_length=8);input:AnalysisStepInput;expected_output:str=Field(min_length=1,max_length=500)
class ChartAgentStep(StrictModel):
    id:str=Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$");tool:Literal["CHART"];purpose:str=Field(min_length=1,max_length=500);depends_on:list[str]=Field(default_factory=list,max_length=8);input:ChartStepInput;expected_output:str=Field(min_length=1,max_length=500)
AgentStep=Annotated[Union[SQLAgentStep,AnalysisAgentStep,ChartAgentStep],Field(discriminator="tool")]
class AgentPlan(StrictModel):goal:str=Field(min_length=1,max_length=1000);summary:str=Field(min_length=1,max_length=2000);steps:list[AgentStep]=Field(min_length=1)
class AgentCreate(StrictModel):
    question:str=Field(min_length=1,max_length=2000)
    @field_validator("question")
    @classmethod
    def strip(cls,v:str)->str:
        v=v.strip()
        if not v:raise ValueError("Question cannot be empty")
        return v
class ToolExecutionResult(StrictModel):
    tool:ToolName;status:Literal["SUCCEEDED","FAILED"];summary:str;columns:list[str]=[];rows:list[list[Any]]=[];row_count:int=0;truncated:bool=False;warnings:list[str]=[];metadata:dict[str,Any]={};artifact_type:str|None=None;artifact_id:str|None=None
class AgentArtifact(StrictModel):type:str;id:str;step_id:str
class AgentFinalResponse(StrictModel):answer:str=Field(min_length=1,max_length=5000);key_findings:list[str]=Field(default_factory=list,max_length=10);limitations:list[str]=Field(default_factory=list,max_length=10);used_tools:list[ToolName]=[];artifacts:list[AgentArtifact]=[]
class AgentStepRead(StrictModel):
    id:str;step_id:str;sequence:int;tool_name:str;purpose:str;status:AgentStepStatus;input_summary_json:dict[str,Any];output_summary_json:dict[str,Any];artifact_type:str|None;artifact_id:str|None;execution_time_ms:float|None;error_code:str|None;error_message:str|None;created_at:datetime;updated_at:datetime
class AgentRunRead(StrictModel):
    id:str;dataset_id:str;user_question:str;goal:str|None;status:AgentRunStatus;planner_summary:str|None;step_count:int;completed_step_count:int;final_summary_json:dict[str,Any];error_code:str|None;error_message:str|None;context_metadata_json:dict[str,Any];created_at:datetime;updated_at:datetime;steps:list[AgentStepRead]=[]
class AgentRunResponse(StrictModel):run:AgentRunRead;plan:AgentPlan|None=None;final:AgentFinalResponse|None=None
class AgentRunList(StrictModel):items:list[AgentRunRead];total:int;page:int;page_size:int
