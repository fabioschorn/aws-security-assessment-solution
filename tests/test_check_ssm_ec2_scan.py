import os
import sys
import types
import zipimport
from pathlib import Path

import pytest


# Utility to load the lambda module from the packaged zip file

def load_lambda_module():
    zip_path = Path(__file__).resolve().parents[1] / (
        "CloudFormation-Templates/modules/RansomwareDetection/"
        "check_ssm_ec2_scan.py.zip"
    )
    loader = zipimport.zipimporter(str(zip_path))
    return loader.load_module("lambda_function")


def test_lambda_handler_no_running_instances(monkeypatch):
    """lambda_handler should succeed when there are no running instances."""

    # Mock boto3 clients
    class MockEC2:
        def describe_instance_status(self):
            return {"InstanceStatuses": []}

    class MockSSM:
        def send_command(self, **kwargs):
            return {}

    def mock_client(service, *args, **kwargs):
        if service == "ec2":
            return MockEC2()
        elif service == "ssm":
            return MockSSM()
        raise ValueError(service)

    mock_boto3 = types.SimpleNamespace(client=mock_client)
    monkeypatch.setitem(sys.modules, "boto3", mock_boto3)

    send_calls = []

    def mock_send(event, context, status, data):
        send_calls.append(status)

    mock_cfn = types.SimpleNamespace(SUCCESS="SUCCESS", send=mock_send)
    monkeypatch.setitem(sys.modules, "cfnresponse", mock_cfn)

    monkeypatch.setenv("reportbucket", "bucket")
    monkeypatch.setenv("ssm_name", "doc")

    mod = load_lambda_module()

    event = {
        "RequestType": "Create",
        "ResponseURL": "http://example.com",
        "StackId": "stack",
        "RequestId": "request",
        "LogicalResourceId": "logical",
    }
    context = types.SimpleNamespace(log_stream_name="log")

    # The function should not raise even if no running instances are found
    mod.lambda_handler(event, context)

    assert send_calls
    assert send_calls[0] == mock_cfn.SUCCESS
