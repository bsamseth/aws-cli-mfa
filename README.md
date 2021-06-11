# aws-cli-mfa
Automate credentials for using AWS CLI with MFA.


* [Who wants this](#who-wants-this)
* [Basic usage](#basic-usage)
  + [Full usage help](#full-usage-help)
* [1Password integration](#1password-integration)
* [Installation](#installation)


## Who wants this

This is a command-line program that allows you to automate setting up credentials for AWS CLI. The program is aimed at the following use-case:

- You have a `~/.aws/credentials` file with credentials for one or more users. For instance:

```conf
[default]
aws_access_key_id = A123456789
aws_secret_access_key = afa9cd8f6ddb6eaa5fdef726d19a4c5c

[other-user]
aws_access_key_id = A987654321
aws_secret_access_key = f1dc490d3dde679f246835210851ab45
```

- You'd like to authenticate with a virtual MFA device (stored in e.g. Google Authenticator, Authy, 1Password, etc.). You may need to do this because the IAM rules say that your user may only perform certain actions of signed in with MFA.
- You like having pre-set profiles in your AWS CLI config, instead of dealing with secrets directly.

Then this tool can help you. 

## Basic usage

If you run 

```bash
aws-cli-mfa default --otp 123456  # Code obtained from your MFA device.
```

you will now have another entry in your credentials file:

```conf
[default-mfa]
aws_access_key_id = A123459876
aws_secret_access_key = 17690d6dd7aa47f64cd43fb7a59c0396
aws_session_token = 7f9dda98758bb2b76e97e45abae266eb2dbf60001ab300d52dc96fa2ce362b3f
aws_session_expiration = <A time stamp 12 hours from now>
```

You can now use this new profile, and it will be a valid MFA login. You use the new profile either by spesifying the profile directly 
```bash
aws s3 ls --profile default-mfa
```
or by setting the `AWS_PROFILE` environment variable.

### Full usage help

Run `aws-cli-mfa --help` to see the full list of options.

```bash
Usage: aws-cli-mfa [OPTIONS] BASE_PROFILE

Arguments:
  BASE_PROFILE  The AWS CLI profile to authenticate.  [env var:
                AWS_PROFILE;required]


Options:
  --aws-credentials-file PATH  The AWS CLI credentials file to update.
                               [default: /home/bendik/.aws/credentials]

  -d, --duration FLOAT RANGE   The number of hours the MFA session should be
                               valid for.  [default: 12]

  --op-item, --op-uuid TEXT    The name or UUID of the 1Password item to get a
                               one-time-password from.

  -p, --otp TEXT               A one-time-password from your MFA device.
  --help                       Show this message and exit.
```

## 1Password integration

1Password users can automatically get the MFA code, instead of manually inputting it. This requires you to install the [1Password CLI tool](https://1password.com/downloads/command-line/), and that you go trough the initial setup (perform one successful login).
You can then run

```bash
aws-cli-mfa <base profile> --op-item <title of login containing OTP>
# or
aws-cli-mfa <base profile> --op-uuid <UUID of login containing OTP>
```

This will prompt you for your master password and fetch the MFA code through the 1Password CLI. 

**Note**: The program assumes you sign in with the command `op signin my` (i.e. you are on a personal plan). Other subdomains are currently not supported (PR welcome).

**Note**: This required `ssh-askpass` to be installed, as this is used to prompt for your master password.

## Installation

This should be easliy installable through pip (or even better, with [pipx](https://pypa.github.io/pipx):
```bash
pip install git+https://github.com/bsamseth/aws-cli-mfa.git
# or 
pip install git+ssh://git@github.com/bsamseth/aws-cli-mfa.git
```
