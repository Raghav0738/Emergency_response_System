#!/usr/bin/env python3
"""CDK application for the low-cost Campus Medical Assistance demo."""

import os

import aws_cdk as cdk

from campus_medical_stack import CampusMedicalDemoStack


app = cdk.App()
CampusMedicalDemoStack(
    app,
    "CampusMedicalDemo",
    termination_protection=True,
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("CDK_DEFAULT_REGION"),
    ),
)
app.synth()
