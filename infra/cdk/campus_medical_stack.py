"""Low-cost, pay-per-request campus medical demo infrastructure."""
from pathlib import Path

from aws_cdk import CfnOutput, CfnParameter, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigatewayv2 as apigwv2, aws_dynamodb as dynamodb
from aws_cdk import aws_ecr_assets as ecr_assets, aws_lambda as lambda_, aws_logs as logs, aws_secretsmanager as secretsmanager
from aws_cdk.aws_apigatewayv2_integrations import HttpLambdaIntegration
from constructs import Construct


class CampusMedicalDemoStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        pages_origin = CfnParameter(
            self,
            "PagesOrigin",
            type="String",
            description="HTTPS origin of your GitHub Pages site, without a path (for example https://username.github.io).",
            allowed_pattern=r"^https://[A-Za-z0-9.-]+(:[0-9]{1,5})?$",
            constraint_description="Enter an HTTPS origin without a path, query, or fragment.",
        )
        admin_email = CfnParameter(
            self,
            "BootstrapAdminEmail",
            type="String",
            description="Email address used for the initial demo administrator account.",
            allowed_pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
            constraint_description="Enter a valid email address.",
        )
        secret = secretsmanager.Secret(self, "ApplicationSecret", generate_secret_string=secretsmanager.SecretStringGenerator(secret_string_template="{}", generate_string_key="jwt_secret", password_length=64, exclude_punctuation=True))
        admin = secretsmanager.Secret(
            self,
            "BootstrapAdmin",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=Stack.of(self).to_json_string(
                    {"email": admin_email.value_as_string}
                ),
                generate_string_key="password",
                password_length=24,
                exclude_punctuation=True,
            ),
        )
        data = dynamodb.Table(
            self,
            "DemoData",
            partition_key=dynamodb.Attribute(name="pk", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="sk", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            deletion_protection=True,
            removal_policy=RemovalPolicy.RETAIN,
        )
        ledger = dynamodb.Table(
            self,
            "IdempotencyLedger",
            partition_key=dynamodb.Attribute(name="request_key", type=dynamodb.AttributeType.STRING),
            time_to_live_attribute="expires_at",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            deletion_protection=True,
            removal_policy=RemovalPolicy.RETAIN,
        )
        repository_root = Path(__file__).resolve().parents[2]
        api_log_group = logs.LogGroup(
            self,
            "ApiLogGroup",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )
        fn = lambda_.DockerImageFunction(
            self,
            "ApiFunction",
            architecture=lambda_.Architecture.X86_64,
            code=lambda_.DockerImageCode.from_image_asset(
                str(repository_root),
                file="Dockerfile.lambda",
                platform=ecr_assets.Platform.LINUX_AMD64,
                exclude=[
                    ".git",
                    ".git/**",
                    ".venv",
                    ".venv/**",
                    "infra/cdk/cdk.out",
                    "infra/cdk/cdk.out/**",
                ],
            ),
            timeout=Duration.seconds(28),
            memory_size=1024,
            log_group=api_log_group,
            environment={
                "ENVIRONMENT": "production",
                "NOTIFICATION_MODE": "simulation",
                "DYNAMO_DEMO_ENABLED": "true",
                "DEMO_DATA_TABLE": data.table_name,
                "IDEMPOTENCY_TABLE": ledger.table_name,
                "APP_SECRET_ARN": secret.secret_arn,
                "BOOTSTRAP_ADMIN_SECRET_ARN": admin.secret_arn,
                "CORS_ORIGINS": Stack.of(self).to_json_string(
                    [pages_origin.value_as_string]
                ),
                "ALLOWED_HOSTS": "[\"*\"]",
            },
        )
        data.grant_read_write_data(fn); ledger.grant_read_write_data(fn); secret.grant_read(fn); admin.grant_read(fn)
        api = apigwv2.HttpApi(self, "HttpApi", cors_preflight=apigwv2.CorsPreflightOptions(allow_origins=[pages_origin.value_as_string], allow_methods=[apigwv2.CorsHttpMethod.ANY], allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Alert-Token"]))
        api.add_routes(path="/{proxy+}", methods=[apigwv2.HttpMethod.ANY], integration=HttpLambdaIntegration("ApiIntegration", fn))
        CfnOutput(self, "ApiBaseUrl", value=api.api_endpoint)
        CfnOutput(self, "BootstrapAdminSecretArn", value=admin.secret_arn)
