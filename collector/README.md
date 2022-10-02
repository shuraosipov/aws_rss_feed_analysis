## About
This project is used to deploy Lambda function that collects data from AWS RSS Feed and stores it in S3 bucket.
Lambda function is triggered by Evenbridge Rule that is scheduled to run every day.


## Installing dependencies

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
