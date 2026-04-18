from datetime import datetime, timezone
from models.models import APIResponse
from typing import Dict,Optional,Any
import traceback
import logging
from dotenv import load_dotenv
from langchain_aws import ChatBedrock
import boto3
import os
from models.models import Error
from datetime import datetime, timezone
load_dotenv()

logger=logging.getLogger(__name__)

def success_response(
    status_code: int,
    message: str,
    data: Optional[Dict],
    request_id: str,
    timestamp: datetime
) -> APIResponse:


    return APIResponse(
        status_code=status_code,
        status="success",
        message=message,
        data=data,
        error=None,
        request_id=request_id,
        timestamp=timestamp
    )

def error_response(
    status_code: int,
    message: str,
    error: Any,
    request_id: str,
    timestamp: datetime
) -> APIResponse:
    return APIResponse(
        status_code=status_code,
        status="error",
        message=message,
        data=None,
        error=Error(  
            error=str(error),
        ),
        request_id=request_id,
        timestamp = timestamp
    )

def log_error(file_name: str,function_name:str,exception:Exception):
    from repository.repository import ErrorLogRepository
    try:
        repo=ErrorLogRepository()
        error_message=str(exception)
        stack_trace=traceback.format_exc()
        full_error=f"{error_message}|TRACE: {stack_trace}"
        repo.store_error(file_name=file_name,function_name=function_name,error=full_error)
    except Exception as e:
        logger.exception("Failed to store error via ErrorLogRepository: %s", e)

def _get_bedrock_client():
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=os.getenv("AWS_REGION")
    )

def get_llm(max_tokens=500, temperature=0.7):

    return ChatBedrock(
        client=_get_bedrock_client(),
        model_id=os.getenv("MODEL_ID"),
        provider=os.getenv("PROVIDER"),
        model_kwargs={
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
    )