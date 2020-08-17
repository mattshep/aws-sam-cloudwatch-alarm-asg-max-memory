import boto3
import logging
from os import environ
from traceback import format_exc
from typing import List, Dict


_running_states = ["Pending", "Pending:Wait", "Pending:Proceed", "InService"]


def generate_metrics_list(asg: str, instances: List[Dict]) -> List[Dict]:

    """
    Builds the metrics list for the aggregate memory alarm.
    """

    ec2 = boto3.client("ec2")

    metrics = list(
        map(
            lambda i: {
                "Id": i["InstanceId"].replace("-", ""),
                "ReturnData": False,
                "MetricStat": {
                    "Metric": {
                        "Namespace": "CWAgent",
                        "MetricName": "Memory % Committed Bytes In Use",
                        "Dimensions": [
                            {"Name": "objectname", "Value": "Memory"},
                            {"Name": "AutoScalingGroupName", "Value": asg},
                            {"Name": "InstanceId", "Value": i["InstanceId"]},
                            {"Name": "InstanceType", "Value": i["InstanceType"]},
                            {
                                "Name": "ImageId",
                                "Value": (
                                    ec2.describe_instances(
                                        InstanceIds=[i["InstanceId"]]
                                    )["Reservations"][0]["Instances"][0]["ImageId"]
                                ),
                            },
                        ],
                    },
                    "Period": int(environ.get("ALARM_PERIOD", 180)),
                    "Stat": "Maximum",
                },
            },
            [i for i in instances],
        )
    ) + [{"Id": "maximum", "Expression": "MAX(METRICS())", "ReturnData": True}]

    return metrics


def lambda_handler(event, context):

    """
    Updates cloudwatch metric alarm for memory usage based on ASG events.
    """

    try:

        # set up logger, default level is INFO
        logger = logging.getLogger()
        log_level = getattr(logging, environ.get("LOG_LEVEL", "INFO"))
        logger.setLevel(log_level)

        # log received event
        logger.warning(f"received event: {event}")

        # ensure required env vars are set
        print(environ)
        sns_topic = environ["SNS_TOPIC"]
        logger.info(f"alarm actions will be posted to {sns_topic}")

        # pick out important information from the group
        asg = event["detail"]["AutoScalingGroupName"]

        # generate alarm name
        alarm = f"{asg}-maximum_memory_utilization"

        # set up boto3 clients
        autoscaling = boto3.client("autoscaling")
        cloudwatch = boto3.client("cloudwatch")

        # describe the auto scaling group
        logger.info(f"fetching list of instance for group {asg}")
        response = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[asg])

        # ensure that information was retrieved
        assert (
            len(response["AutoScalingGroups"]) > 0
        ), f"failed to find any group with name {asg}"

        # grab list of autoscaling group instances
        instances = response["AutoScalingGroups"][0]["Instances"]
        assert len(instances) > 0, f"group {asg} has 0 running instances"
        logger.info(f"retrieved list of {len(instances)} instances for group {asg}")

        # determine which instances are in a running state
        running_instances = []
        for i in instances:
            if i["LifecycleState"] in _running_states:
                logger.info(f"instance {i['InstanceId']} is in a running state")
                running_instances.append(i)

        # build alarm definition
        request_params = {
            "AlarmName": alarm,
            "AlarmDescription": (
                f"Alert when maximum memory utilization for an instance in {asg}"
                f"autoscaling group surpasses 80%."
            ),
            "ActionsEnabled": True,
            "OKActions": [sns_topic],
            "AlarmActions": [sns_topic],
            "InsufficientDataActions": [sns_topic],
            "EvaluationPeriods": int(environ.get("ALARM_EVALUATION_PERIODS", 10)),
            "Threshold": int(environ.get("ALARM_THRESHOLD", 75)),
            "ComparisonOperator": "GreaterThanThreshold",
            "Metrics": generate_metrics_list(asg, running_instances),
        }
        logger.info(f"ready to put new alarm definition: {str(request_params)}")
        response = cloudwatch.put_metric_alarm(**request_params)
        logger.info(f"successfully created or updated alarm {alarm}")

        return {"success": True, "result": response}

    except Exception:

        logger.exception("unhandled exception")

        raise
