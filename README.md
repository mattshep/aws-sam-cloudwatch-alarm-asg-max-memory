# aws-sam-cloudwatch-alarm-asg-max-memory

[![License](https://img.shields.io/github/license/mattshep/aws-sam-cloudwatch-alarm-asg-max-memory)](https://github.com/mattshep/aws-sam-cloudwatch-alarm-asg-max-memory/blob/master/LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

AWS SAM application to maintain CloudWatch alarms for maximum AutoScalingGroup memory utilization. When the maximum memory utliization, as a percentage of the instance's total memory, exceeds the configured threshold then the alarm will enter an Alarm state. All state changes are published to the configured SNS topic.

Instances in monitored AutoScaling groups must implement enhanced monitoring using the [CloudWatch Agent](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html).

Default EC2 instance metrics do not include any memory metrics, and there is an extra cost associated with the collection of custom metrics. Refer to the official AWS documentation for more information on the cost for custom CloudWatch metrics: https://aws.amazon.com/cloudwatch/pricing/ 

## License

This project is licensed under the Apache-2.0 License.

## Why?

Because [CloudWatch alarms do not support search expressions](https://stackoverflow.com/a/55826445/9603546). Seriously, that's all. I wanted to use something like this:

    MAX( SEARCH( ' {CWAgent,AutoScalingGroupName,ImageId,InstanceId,InstanceType,objectname} AutoScalingGroupName="<group>" MetricName="Memory % Committed Bytes In Use" ', 'Maximum', 300 ) )

Instead I needed something that can keep my list of "child" metrics up-to-date as group membership changed. `¯\_(ツ)_/¯`

## Usage

Deploy using the [aws-sam-cli](https://github.com/awslabs/aws-sam-cli) tool.

    > sam deploy -g
    Configuring SAM deploy
    ======================
    
        Looking for samconfig.toml :  Not found

        Setting default arguments for 'sam deploy'
        =========================================
        Stack Name [sam-app]:
        AWS Region [us-east-1]:
        Parameter SNSTopic []: <topic>
        Parameter AutoScalingGroups []: <groups>
        Parameter AlarmPeriod [180]:
        Parameter AlarmThreshold [75]:
        Parameter AlarmEvaluationPeriods [10]:
        #Shows you resources changes to be deployed and require a 'Y' to initiate deploy
        Confirm changes before deploy [y/N]: Y
        #SAM needs permission to be able to create roles to connect to the resources in your template
        Allow SAM CLI IAM role creation [Y/n]: Y
        Save arguments to samconfig.toml [Y/n]: Y
        ...

To receive notifications for alarm state changes, ensure that the provided SNS topic has the appropriate subscriptions.
