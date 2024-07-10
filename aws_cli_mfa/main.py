import configparser
import json
import subprocess
from pathlib import Path

import boto3
import typer


def capture_output(args, check=True, input=None):
    return (
        subprocess.run(args, check=check, input=input, capture_output=True)
        .stdout.decode()
        .rstrip()
    )


def _askpass(prompt=""):
    try:
        subprocess.run(["which", "ssh-askpass"], check=True)
    except subprocess.CalledProcessError:
        typer.secho("Please install 'ssh-askpass' and try again.", fg=typer.colors.RED)
        raise typer.Exit(2)
    return capture_output(["ssh-askpass", prompt])


def _1password_signin(master_password):
    try:
        return capture_output(["op", "signin", "--raw"], input=master_password.encode())
    except subprocess.CalledProcessError:
        typer.secho(
            "Failed to login to 1Password (incorrect password?)", fg=typer.colors.RED
        )
        typer.echo(
            "Please run 'op signin my' to verify that you can login, then try again."
        )
        raise typer.Exit(3)


def _1password_otp(item_or_uuid):
    return json.loads(
        capture_output(
            [
                "op",
                "item",
                "get",
                item_or_uuid,
                "--field",
                "type=otp",
                "--format",
                "json",
                "--session",
                _1password_signin(_askpass()),
            ]
        )
    )["totp"]


def main(
    base_profile: str = typer.Argument(
        ..., envvar="AWS_PROFILE", help="The AWS CLI profile to authenticate."
    ),
    aws_credentials_file: Path = typer.Option(
        Path("~/.aws/credentials").expanduser(),
        help="The AWS CLI credentials file to update.",
        exists=True,
        readable=True,
        writable=True,
    ),
    session_duration: float = typer.Option(
        12,
        "-d",
        "--duration",
        min=0,
        max=36,
        help="The number of hours the MFA session should be valid for.",
    ),
    op_item_or_uuid: str = typer.Option(
        None,
        "--op-item",
        "--op-uuid",
        help="The name or UUID of the 1Password item to get a one-time-password from.",
    ),
    one_time_password: str = typer.Option(
        None, "-p", "--otp", help="A one-time-password from your MFA device."
    ),
    mfa_device_to_use: str = typer.Option(
        None, 
        "-m", "--mfa-device", help="The name of the mfa device to use"
    )
):
    if not (one_time_password or op_item_or_uuid):
        typer.secho(
            "One of --otp, --op-item, or --op-uuid must be provided.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    otp = one_time_password or _1password_otp(op_item_or_uuid)
    typer.secho("Acquired OTP", fg=typer.colors.GREEN)

    boto_session = boto3.session.Session(profile_name=base_profile)
    sts = boto_session.client("sts")
    iam = boto_session.client("iam")

    mfa_devices = iam.list_mfa_devices()
    if not mfa_devices['MFADevices']:
        typer.secho(
            "No MFA devices configured for this account found",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    if mfa_device_to_use:
        mfa_devices_dict = {d['SerialNumber'].split('/')[-1]: d for d in mfa_devices['MFADevices']}
        if mfa_device_to_use not in mfa_devices_dict.keys():
            typer.secho(
                f"No MFA device named '{mfa_device_to_use}' found. List of mfa devices configured: {', '.join(mfa_devices_dict.keys())}",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)
        mfa_device = mfa_devices_dict[mfa_device_to_use]
    else:
        mfa_device = mfa_devices['MFADevices'][0]
    typer.secho(f"Using MFA Device: {mfa_device['SerialNumber']}", fg=typer.colors.GREEN)


    session_token = sts.get_session_token(
        DurationSeconds=int(session_duration * 60 * 60),
        SerialNumber=mfa_device['SerialNumber'],
        TokenCode=otp,
    )
    typer.secho("Acquired MFA session from AWS STS", fg=typer.colors.GREEN)

    config = configparser.ConfigParser()
    config.read(aws_credentials_file)
    config[f"{base_profile}-mfa"] = {
        "aws_access_key_id": session_token["Credentials"]["AccessKeyId"],
        "aws_secret_access_key": session_token["Credentials"]["SecretAccessKey"],
        "aws_session_token": session_token["Credentials"]["SessionToken"],
        "aws_session_expiration": session_token["Credentials"][
            "Expiration"
        ].isoformat(),
    }
    with open(aws_credentials_file, "w") as f:
        config.write(f)

    typer.echo(
        typer.style("Successfully updated ", fg=typer.colors.BRIGHT_GREEN)
        + typer.style(str(aws_credentials_file), fg=typer.colors.BRIGHT_MAGENTA)
        + typer.style(" with a new MFA profile: ", fg=typer.colors.BRIGHT_GREEN)
        + typer.style(f"{base_profile}-mfa", fg=typer.colors.BRIGHT_MAGENTA),
    )


app = typer.Typer(add_completion=False)
app.command()(main)

if __name__ == "__main__":
    app()
