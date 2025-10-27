# Pulumi ESC Integration

This project uses Pulumi ESC (Environment, Secrets, and Configuration) as the centralized source of truth for all configuration and secrets.

## How It Works

### ESC Environment Structure

The ESC environment (`default/knock-lambda-esc`) has three key sections:

```yaml
values:
  # 1. Raw configuration values
  AWS_REGION: us-east-2
  DOCKER_HUB_USERNAME: l0gan
  DOCKER_HUB_TOKEN:
    fn::secret: <encrypted> # Secrets wrapped with fn::secret
  VARIABLE_EDITING_PAT:
    fn::secret: <encrypted>

  # 2. pulumiConfig - Exposes values to Pulumi stacks
  pulumiConfig:
    aws:region: ${AWS_REGION}
    knock-lambda:DOCKER_HUB_USERNAME: ${DOCKER_HUB_USERNAME}
    knock-lambda:DOCKER_HUB_TOKEN: ${DOCKER_HUB_TOKEN}
    knock-lambda:VARIABLE_EDITING_PAT: ${VARIABLE_EDITING_PAT}

  # 3. environmentVariables - For GitHub Actions and 'esc run'
  environmentVariables:
    AWS_REGION: ${AWS_REGION}
    DOCKER_HUB_USERNAME: ${DOCKER_HUB_USERNAME}
    DOCKER_HUB_TOKEN: ${DOCKER_HUB_TOKEN}
    VARIABLE_EDITING_PAT: ${VARIABLE_EDITING_PAT}
```

### Integration Points

#### 1. **Pulumi Stack Configuration** (`Pulumi.dev.yaml`, `Pulumi.main.yaml`)

```yaml
environment:
  - default/knock-lambda-esc
```

This automatically imports the ESC environment and makes `pulumiConfig` values available via the standard Pulumi Config API.

#### 2. **Python Code** (`infrastructure/vars.py`)

```python
import pulumi

config = pulumi.Config()

# Read from pulumiConfig section
AWS_REGION = config.get("aws:region")  # From pulumiConfig.aws:region
DOCKER_HUB_USERNAME = config.require("DOCKER_HUB_USERNAME")  # From pulumiConfig.knock-lambda:DOCKER_HUB_USERNAME
DOCKER_HUB_TOKEN = config.require_secret("DOCKER_HUB_TOKEN")  # From pulumiConfig.knock-lambda:DOCKER_HUB_TOKEN (secret)
```

#### 3. **GitHub Actions** (`.github/workflows/pulumi.yml`)

```yaml
- uses: pulumi/esc-action@v1
  with:
    environment: default/knock-lambda-esc
  id: esc

# Access via environment variables
- run: echo $AWS_REGION
  env:
    AWS_REGION: ${{ steps.esc.outputs.AWS_REGION }}
```

## Setup

Run the setup script to configure your ESC environment:

```bash
uv run scripts/setup.py
```

This will:

1. Create or update the `default/knock-lambda-esc` environment
2. Prompt for any missing configuration values
3. Store secrets securely (wrapped with `fn::secret`)
4. Structure the environment with `pulumiConfig` and `environmentVariables` sections

## Usage

### View Configuration

```bash
# View all values (secrets shown as [secret])
esc env get default/knock-lambda-esc

# Open environment (resolves secrets - requires permissions)
esc env open default/knock-lambda-esc

# View Pulumi config (shows what's available to Pulumi stacks)
pulumi config
```

### Update Configuration

```bash
# Edit the environment
esc env edit default/knock-lambda-esc

# Or re-run setup script
uv run scripts/setup.py
```

### Deploy with ESC

```bash
# Dev stack (automatically loads ESC environment from Pulumi.dev.yaml)
pulumi stack select dev
pulumi up

# Base stack (needs explicit esc run because it doesn't import ESC)
pulumi stack select base
esc run default/knock-lambda-esc -- pulumi up
```

## Benefits

✅ **Centralized Configuration**: Single source of truth for all environments  
✅ **Secure Secrets**: Encrypted at rest, access controlled via Pulumi Cloud  
✅ **No Local Files**: No `.env` files with secrets to accidentally commit  
✅ **Team Friendly**: Easy to share configuration via Pulumi Cloud permissions  
✅ **Fork Friendly**: Forkers create their own ESC environment, no GitHub secrets needed  
✅ **Standard APIs**: Uses standard Pulumi Config API - no custom code needed

## Architecture

```
ESC Environment (default/knock-lambda-esc)
├── values (raw config + secrets)
├── pulumiConfig (→ Pulumi Config API)
└── environmentVariables (→ GitHub Actions, esc run)

Pulumi Stacks
├── base (doesn't import ESC - chicken/egg with OIDC)
├── dev (imports ESC via Pulumi.dev.yaml)
└── main (imports ESC via Pulumi.main.yaml)
```

## References

- [Pulumi ESC Documentation](https://www.pulumi.com/docs/esc/)
- [Using ESC with Pulumi IaC](https://www.pulumi.com/docs/esc/environments/working-with-environments/#using-environments-with-pulumi-iac)
- [ESC CLI Reference](https://www.pulumi.com/docs/esc-cli/)
