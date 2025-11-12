"""
CI/CD Integration Service for Arduino IDE Modern

This service provides comprehensive CI/CD integration capabilities for Arduino projects,
supporting multiple platforms including GitHub Actions, GitLab CI, and Jenkins.

Features:
- Pipeline configuration generation
- Build status monitoring
- Automated testing integration
- Deployment workflows
- Build artifact management
- Multi-platform support
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set
import json
import re
import subprocess
import yaml
import requests
from urllib.parse import urlparse

from PySide6.QtCore import QObject, Signal, QTimer


class CICDPlatform(Enum):
    """Supported CI/CD platforms"""
    GITHUB_ACTIONS = "github_actions"
    GITLAB_CI = "gitlab_ci"
    JENKINS = "jenkins"
    TRAVIS_CI = "travis_ci"
    CIRCLE_CI = "circle_ci"
    AZURE_PIPELINES = "azure_pipelines"


class BuildStatus(Enum):
    """Build status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class DeploymentEnvironment(Enum):
    """Deployment environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class BuildJob:
    """Represents a single build job"""
    id: str
    name: str
    status: BuildStatus
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    log_url: str = ""
    artifacts: List[str] = field(default_factory=list)
    error_message: str = ""

    def is_running(self) -> bool:
        """Check if job is running"""
        return self.status == BuildStatus.RUNNING

    def is_finished(self) -> bool:
        """Check if job is finished"""
        return self.status in [BuildStatus.SUCCESS, BuildStatus.FAILED, BuildStatus.CANCELLED]


@dataclass
class Pipeline:
    """Represents a CI/CD pipeline"""
    id: str
    name: str
    platform: CICDPlatform
    branch: str
    commit_sha: str
    commit_message: str
    status: BuildStatus
    jobs: List[BuildJob] = field(default_factory=list)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    triggered_by: str = ""
    web_url: str = ""

    def add_job(self, job: BuildJob):
        """Add a job to this pipeline"""
        self.jobs.append(job)

    def total_duration_seconds(self) -> float:
        """Get total duration"""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return 0.0

    def success_rate(self) -> float:
        """Calculate success rate of jobs"""
        if not self.jobs:
            return 0.0
        successful = sum(1 for job in self.jobs if job.status == BuildStatus.SUCCESS)
        return (successful / len(self.jobs)) * 100.0


@dataclass
class PipelineConfiguration:
    """CI/CD pipeline configuration"""
    platform: CICDPlatform
    name: str = "Arduino CI/CD"
    triggers: List[str] = field(default_factory=lambda: ["push", "pull_request"])
    branches: List[str] = field(default_factory=lambda: ["main", "develop"])
    build_matrix: Dict[str, List[str]] = field(default_factory=dict)
    enable_testing: bool = True
    enable_linting: bool = True
    enable_deployment: bool = False
    deployment_env: DeploymentEnvironment = DeploymentEnvironment.DEVELOPMENT
    arduino_cli_version: str = "latest"
    boards: List[str] = field(default_factory=lambda: ["arduino:avr:uno"])
    timeout_minutes: int = 30
    cache_enabled: bool = True
    artifact_retention_days: int = 7


@dataclass
class Deployment:
    """Represents a deployment"""
    id: str
    environment: DeploymentEnvironment
    status: BuildStatus
    version: str
    commit_sha: str
    deployed_at: Optional[datetime] = None
    deployed_by: str = ""
    url: str = ""
    rollback_available: bool = False


class CICDService(QObject):
    """
    Service for managing CI/CD pipelines

    Signals:
        pipeline_created: Emitted when a pipeline is created
        pipeline_started: Emitted when a pipeline starts
        pipeline_finished: Emitted when a pipeline finishes
        job_started: Emitted when a job starts
        job_finished: Emitted when a job finishes
        deployment_started: Emitted when deployment starts
        deployment_finished: Emitted when deployment finishes
    """

    # Signals
    pipeline_created = Signal(Pipeline)
    pipeline_started = Signal(Pipeline)
    pipeline_finished = Signal(Pipeline)
    job_started = Signal(BuildJob)
    job_finished = Signal(BuildJob)
    deployment_started = Signal(Deployment)
    deployment_finished = Signal(Deployment)

    def __init__(self, project_path: str = ""):
        super().__init__()

        self.project_path = Path(project_path) if project_path else Path.cwd()

        # Pipeline data
        self.pipelines: Dict[str, Pipeline] = {}
        self.deployments: Dict[str, Deployment] = {}
        self.configuration = PipelineConfiguration(platform=CICDPlatform.GITHUB_ACTIONS)

        # Platform credentials
        self.github_token: Optional[str] = None
        self.gitlab_token: Optional[str] = None
        self.jenkins_credentials: Optional[Dict[str, str]] = None

        # Monitoring
        self.monitoring_timer = QTimer()
        self.monitoring_timer.timeout.connect(self._check_pipeline_status)
        self.monitoring_enabled = False

    def set_project_path(self, path: str):
        """Set the project path"""
        self.project_path = Path(path)

    def set_configuration(self, config: PipelineConfiguration):
        """Set pipeline configuration"""
        self.configuration = config

    def set_github_token(self, token: str):
        """Set GitHub personal access token"""
        self.github_token = token

    def set_gitlab_token(self, token: str):
        """Set GitLab personal access token"""
        self.gitlab_token = token

    def set_jenkins_credentials(self, username: str, token: str, url: str):
        """Set Jenkins credentials"""
        self.jenkins_credentials = {
            'username': username,
            'token': token,
            'url': url
        }

    def generate_pipeline_config(self, platform: Optional[CICDPlatform] = None) -> str:
        """
        Generate pipeline configuration file for the specified platform

        Args:
            platform: Target platform (uses config if not specified)

        Returns:
            Path to generated configuration file
        """
        if platform is None:
            platform = self.configuration.platform

        if platform == CICDPlatform.GITHUB_ACTIONS:
            return self._generate_github_actions_config()
        elif platform == CICDPlatform.GITLAB_CI:
            return self._generate_gitlab_ci_config()
        elif platform == CICDPlatform.JENKINS:
            return self._generate_jenkinsfile()
        elif platform == CICDPlatform.TRAVIS_CI:
            return self._generate_travis_config()
        elif platform == CICDPlatform.CIRCLE_CI:
            return self._generate_circleci_config()
        elif platform == CICDPlatform.AZURE_PIPELINES:
            return self._generate_azure_pipelines_config()

        return ""

    def _generate_github_actions_config(self) -> str:
        """Generate GitHub Actions workflow file"""
        config = self.configuration

        workflow = {
            'name': config.name,
            'on': {}
        }

        # Triggers
        if 'push' in config.triggers:
            workflow['on']['push'] = {
                'branches': config.branches
            }
        if 'pull_request' in config.triggers:
            workflow['on']['pull_request'] = {
                'branches': config.branches
            }

        # Jobs
        jobs = {}

        # Build job
        build_job = {
            'runs-on': 'ubuntu-latest',
            'timeout-minutes': config.timeout_minutes,
            'steps': []
        }

        # Checkout
        build_job['steps'].append({
            'name': 'Checkout code',
            'uses': 'actions/checkout@v3'
        })

        # Setup Arduino CLI
        build_job['steps'].append({
            'name': 'Setup Arduino CLI',
            'uses': 'arduino/setup-arduino-cli@v1',
            'with': {
                'version': config.arduino_cli_version
            }
        })

        # Update board index
        build_job['steps'].append({
            'name': 'Update board index',
            'run': 'arduino-cli core update-index'
        })

        # Install cores
        for board in config.boards:
            platform_id = ':'.join(board.split(':')[:2])
            build_job['steps'].append({
                'name': f'Install {platform_id}',
                'run': f'arduino-cli core install {platform_id}'
            })

        # Install libraries
        build_job['steps'].append({
            'name': 'Install libraries',
            'run': 'arduino-cli lib install --git-url https://github.com/arduino-libraries'
        })

        # Compile sketch
        for board in config.boards:
            build_job['steps'].append({
                'name': f'Compile for {board}',
                'run': f'arduino-cli compile --fqbn {board} .'
            })

        # Testing
        if config.enable_testing:
            build_job['steps'].append({
                'name': 'Run tests',
                'run': 'make test || echo "No tests configured"'
            })

        # Linting
        if config.enable_linting:
            build_job['steps'].append({
                'name': 'Run cpplint',
                'run': 'pip install cpplint && cpplint --recursive src/ || echo "Linting warnings"'
            })

        # Upload artifacts
        build_job['steps'].append({
            'name': 'Upload build artifacts',
            'uses': 'actions/upload-artifact@v3',
            'with': {
                'name': 'firmware',
                'path': 'build/**/*.hex',
                'retention-days': config.artifact_retention_days
            }
        })

        jobs['build'] = build_job

        # Test job
        if config.enable_testing:
            test_job = {
                'runs-on': 'ubuntu-latest',
                'needs': 'build',
                'steps': [
                    {
                        'name': 'Checkout code',
                        'uses': 'actions/checkout@v3'
                    },
                    {
                        'name': 'Setup test environment',
                        'run': 'sudo apt-get install -y googletest lcov'
                    },
                    {
                        'name': 'Run unit tests',
                        'run': 'make test-coverage'
                    },
                    {
                        'name': 'Upload coverage',
                        'uses': 'codecov/codecov-action@v3',
                        'with': {
                            'files': './coverage.xml'
                        }
                    }
                ]
            }
            jobs['test'] = test_job

        # Deploy job
        if config.enable_deployment:
            deploy_job = {
                'runs-on': 'ubuntu-latest',
                'needs': ['build', 'test'] if config.enable_testing else ['build'],
                'if': "github.ref == 'refs/heads/main'",
                'environment': config.deployment_env.value,
                'steps': [
                    {
                        'name': 'Checkout code',
                        'uses': 'actions/checkout@v3'
                    },
                    {
                        'name': 'Download artifacts',
                        'uses': 'actions/download-artifact@v3',
                        'with': {
                            'name': 'firmware'
                        }
                    },
                    {
                        'name': 'Deploy firmware',
                        'run': 'echo "Deploy to ${{ env.DEPLOY_TARGET }}"'
                    }
                ]
            }
            jobs['deploy'] = deploy_job

        workflow['jobs'] = jobs

        # Write to file
        workflow_dir = self.project_path / '.github' / 'workflows'
        workflow_dir.mkdir(parents=True, exist_ok=True)
        workflow_file = workflow_dir / 'arduino-ci.yml'

        with open(workflow_file, 'w') as f:
            yaml.dump(workflow, f, default_flow_style=False, sort_keys=False)

        return str(workflow_file)

    def _generate_gitlab_ci_config(self) -> str:
        """Generate GitLab CI configuration"""
        config = self.configuration

        gitlab_config = {
            'image': 'python:3.9',
            'stages': ['build', 'test', 'deploy'],
            'variables': {
                'ARDUINO_CLI_VERSION': config.arduino_cli_version
            }
        }

        # Before script
        gitlab_config['before_script'] = [
            'apt-get update',
            'apt-get install -y wget',
            'wget https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Linux_64bit.tar.gz',
            'tar -xzf arduino-cli_latest_Linux_64bit.tar.gz',
            'mv arduino-cli /usr/local/bin/',
            'arduino-cli core update-index'
        ]

        # Build job
        build_job = {
            'stage': 'build',
            'script': []
        }

        for board in config.boards:
            platform_id = ':'.join(board.split(':')[:2])
            build_job['script'].append(f'arduino-cli core install {platform_id}')
            build_job['script'].append(f'arduino-cli compile --fqbn {board} .')

        build_job['artifacts'] = {
            'paths': ['build/'],
            'expire_in': f'{config.artifact_retention_days} days'
        }

        build_job['only'] = config.branches

        gitlab_config['build'] = build_job

        # Test job
        if config.enable_testing:
            test_job = {
                'stage': 'test',
                'script': [
                    'apt-get install -y googletest lcov',
                    'make test-coverage'
                ],
                'coverage': '/^TOTAL.*\\s+(\\d+%)$/',
                'artifacts': {
                    'reports': {
                        'coverage_report': {
                            'coverage_format': 'cobertura',
                            'path': 'coverage.xml'
                        }
                    }
                }
            }
            gitlab_config['test'] = test_job

        # Deploy job
        if config.enable_deployment:
            deploy_job = {
                'stage': 'deploy',
                'script': [
                    'echo "Deploying to ${CI_ENVIRONMENT_NAME}"'
                ],
                'environment': {
                    'name': config.deployment_env.value
                },
                'only': ['main']
            }
            gitlab_config['deploy'] = deploy_job

        # Write to file
        config_file = self.project_path / '.gitlab-ci.yml'
        with open(config_file, 'w') as f:
            yaml.dump(gitlab_config, f, default_flow_style=False, sort_keys=False)

        return str(config_file)

    def _generate_jenkinsfile(self) -> str:
        """Generate Jenkinsfile"""
        config = self.configuration

        jenkinsfile = """pipeline {
    agent any

    environment {
        ARDUINO_CLI = '/usr/local/bin/arduino-cli'
    }

    stages {
        stage('Setup') {
            steps {
                sh 'wget https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Linux_64bit.tar.gz'
                sh 'tar -xzf arduino-cli_latest_Linux_64bit.tar.gz'
                sh 'sudo mv arduino-cli /usr/local/bin/'
                sh 'arduino-cli core update-index'
            }
        }

        stage('Build') {
            steps {
"""

        for board in config.boards:
            platform_id = ':'.join(board.split(':')[:2])
            jenkinsfile += f"                sh 'arduino-cli core install {platform_id}'\n"
            jenkinsfile += f"                sh 'arduino-cli compile --fqbn {board} .'\n"

        jenkinsfile += """            }
        }
"""

        if config.enable_testing:
            jenkinsfile += """
        stage('Test') {
            steps {
                sh 'apt-get install -y googletest'
                sh 'make test'
            }
        }
"""

        if config.enable_deployment:
            jenkinsfile += f"""
        stage('Deploy') {{
            when {{
                branch 'main'
            }}
            steps {{
                echo 'Deploying to {config.deployment_env.value}'
            }}
        }}
"""

        jenkinsfile += """    }

    post {
        always {
            archiveArtifacts artifacts: 'build/**/*.hex', allowEmptyArchive: true
        }
        success {
            echo 'Build successful!'
        }
        failure {
            echo 'Build failed!'
        }
    }
}
"""

        # Write to file
        jenkinsfile_path = self.project_path / 'Jenkinsfile'
        jenkinsfile_path.write_text(jenkinsfile)

        return str(jenkinsfile_path)

    def _generate_travis_config(self) -> str:
        """Generate Travis CI configuration"""
        config = self.configuration

        travis_config = {
            'language': 'python',
            'python': ['3.9'],
            'branches': {
                'only': config.branches
            },
            'before_install': [
                'wget https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Linux_64bit.tar.gz',
                'tar -xzf arduino-cli_latest_Linux_64bit.tar.gz',
                'sudo mv arduino-cli /usr/local/bin/',
                'arduino-cli core update-index'
            ],
            'install': []
        }

        for board in config.boards:
            platform_id = ':'.join(board.split(':')[:2])
            travis_config['install'].append(f'arduino-cli core install {platform_id}')

        travis_config['script'] = []
        for board in config.boards:
            travis_config['script'].append(f'arduino-cli compile --fqbn {board} .')

        if config.enable_testing:
            travis_config['script'].append('make test')

        # Write to file
        config_file = self.project_path / '.travis.yml'
        with open(config_file, 'w') as f:
            yaml.dump(travis_config, f, default_flow_style=False)

        return str(config_file)

    def _generate_circleci_config(self) -> str:
        """Generate CircleCI configuration"""
        config = self.configuration

        circleci_config = {
            'version': 2.1,
            'jobs': {
                'build': {
                    'docker': [{'image': 'cimg/python:3.9'}],
                    'steps': [
                        'checkout',
                        {
                            'run': {
                                'name': 'Setup Arduino CLI',
                                'command': """
wget https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Linux_64bit.tar.gz
tar -xzf arduino-cli_latest_Linux_64bit.tar.gz
sudo mv arduino-cli /usr/local/bin/
arduino-cli core update-index
"""
                            }
                        }
                    ]
                }
            }
        }

        # Add compile steps
        for board in config.boards:
            platform_id = ':'.join(board.split(':')[:2])
            circleci_config['jobs']['build']['steps'].append({
                'run': {
                    'name': f'Compile for {board}',
                    'command': f'arduino-cli core install {platform_id} && arduino-cli compile --fqbn {board} .'
                }
            })

        # Workflow
        circleci_config['workflows'] = {
            'version': 2,
            'build_and_test': {
                'jobs': ['build']
            }
        }

        # Write to file
        config_dir = self.project_path / '.circleci'
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / 'config.yml'

        with open(config_file, 'w') as f:
            yaml.dump(circleci_config, f, default_flow_style=False)

        return str(config_file)

    def _generate_azure_pipelines_config(self) -> str:
        """Generate Azure Pipelines configuration"""
        config = self.configuration

        azure_config = {
            'trigger': config.branches,
            'pool': {
                'vmImage': 'ubuntu-latest'
            },
            'steps': [
                {
                    'task': 'Bash@3',
                    'displayName': 'Setup Arduino CLI',
                    'inputs': {
                        'targetType': 'inline',
                        'script': """
wget https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Linux_64bit.tar.gz
tar -xzf arduino-cli_latest_Linux_64bit.tar.gz
sudo mv arduino-cli /usr/local/bin/
arduino-cli core update-index
"""
                    }
                }
            ]
        }

        # Add compile steps
        for board in config.boards:
            platform_id = ':'.join(board.split(':')[:2])
            azure_config['steps'].append({
                'task': 'Bash@3',
                'displayName': f'Compile for {board}',
                'inputs': {
                    'targetType': 'inline',
                    'script': f'arduino-cli core install {platform_id}\narduino-cli compile --fqbn {board} .'
                }
            })

        # Write to file
        config_file = self.project_path / 'azure-pipelines.yml'
        with open(config_file, 'w') as f:
            yaml.dump(azure_config, f, default_flow_style=False)

        return str(config_file)

    def fetch_pipelines(self, limit: int = 10) -> List[Pipeline]:
        """
        Fetch recent pipelines from the platform

        Args:
            limit: Maximum number of pipelines to fetch

        Returns:
            List of pipelines
        """
        platform = self.configuration.platform

        if platform == CICDPlatform.GITHUB_ACTIONS:
            return self._fetch_github_pipelines(limit)
        elif platform == CICDPlatform.GITLAB_CI:
            return self._fetch_gitlab_pipelines(limit)
        elif platform == CICDPlatform.JENKINS:
            return self._fetch_jenkins_pipelines(limit)

        return []

    def _fetch_github_pipelines(self, limit: int) -> List[Pipeline]:
        """Fetch pipelines from GitHub Actions"""
        if not self.github_token:
            return []

        try:
            # Get repository info from git remote
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                cwd=str(self.project_path),
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return []

            # Parse repository from remote URL
            remote_url = result.stdout.strip()
            repo_match = re.search(r'github\.com[:/](.+)/(.+?)(?:\.git)?$', remote_url)
            if not repo_match:
                return []

            owner, repo = repo_match.groups()

            # Fetch workflow runs
            api_url = f'https://api.github.com/repos/{owner}/{repo}/actions/runs'
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }

            response = requests.get(
                api_url,
                headers=headers,
                params={'per_page': limit}
            )

            if response.status_code != 200:
                return []

            data = response.json()
            pipelines = []

            for run in data.get('workflow_runs', []):
                pipeline = Pipeline(
                    id=str(run['id']),
                    name=run['name'],
                    platform=CICDPlatform.GITHUB_ACTIONS,
                    branch=run['head_branch'],
                    commit_sha=run['head_sha'],
                    commit_message=run.get('head_commit', {}).get('message', ''),
                    status=self._map_github_status(run['status'], run['conclusion']),
                    started_at=datetime.fromisoformat(run['created_at'].replace('Z', '+00:00')) if run.get('created_at') else None,
                    finished_at=datetime.fromisoformat(run['updated_at'].replace('Z', '+00:00')) if run.get('updated_at') else None,
                    triggered_by=run.get('triggering_actor', {}).get('login', ''),
                    web_url=run['html_url']
                )

                pipelines.append(pipeline)
                self.pipelines[pipeline.id] = pipeline

            return pipelines

        except Exception as e:
            print(f"Error fetching GitHub pipelines: {e}")
            return []

    def _map_github_status(self, status: str, conclusion: Optional[str]) -> BuildStatus:
        """Map GitHub Actions status to BuildStatus"""
        if status == 'completed':
            if conclusion == 'success':
                return BuildStatus.SUCCESS
            elif conclusion == 'failure':
                return BuildStatus.FAILED
            elif conclusion == 'cancelled':
                return BuildStatus.CANCELLED
            elif conclusion == 'skipped':
                return BuildStatus.SKIPPED
        elif status == 'in_progress':
            return BuildStatus.RUNNING
        elif status == 'queued':
            return BuildStatus.PENDING

        return BuildStatus.PENDING

    def _fetch_gitlab_pipelines(self, limit: int) -> List[Pipeline]:
        """Fetch pipelines from GitLab CI"""
        if not self.gitlab_token:
            return []

        try:
            # Get project ID from git remote
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                cwd=str(self.project_path),
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return []

            remote_url = result.stdout.strip()
            project_match = re.search(r'gitlab\.com[:/](.+?)(?:\.git)?$', remote_url)
            if not project_match:
                return []

            project_path = project_match.group(1)
            project_id = project_path.replace('/', '%2F')

            # Fetch pipelines
            api_url = f'https://gitlab.com/api/v4/projects/{project_id}/pipelines'
            headers = {
                'PRIVATE-TOKEN': self.gitlab_token
            }

            response = requests.get(
                api_url,
                headers=headers,
                params={'per_page': limit}
            )

            if response.status_code != 200:
                return []

            data = response.json()
            pipelines = []

            for pipeline_data in data:
                pipeline = Pipeline(
                    id=str(pipeline_data['id']),
                    name=f"Pipeline #{pipeline_data['id']}",
                    platform=CICDPlatform.GITLAB_CI,
                    branch=pipeline_data['ref'],
                    commit_sha=pipeline_data['sha'],
                    commit_message='',
                    status=self._map_gitlab_status(pipeline_data['status']),
                    started_at=datetime.fromisoformat(pipeline_data['created_at'].replace('Z', '+00:00')) if pipeline_data.get('created_at') else None,
                    finished_at=datetime.fromisoformat(pipeline_data['updated_at'].replace('Z', '+00:00')) if pipeline_data.get('updated_at') else None,
                    web_url=pipeline_data['web_url']
                )

                pipelines.append(pipeline)
                self.pipelines[pipeline.id] = pipeline

            return pipelines

        except Exception as e:
            print(f"Error fetching GitLab pipelines: {e}")
            return []

    def _map_gitlab_status(self, status: str) -> BuildStatus:
        """Map GitLab status to BuildStatus"""
        status_map = {
            'pending': BuildStatus.PENDING,
            'running': BuildStatus.RUNNING,
            'success': BuildStatus.SUCCESS,
            'failed': BuildStatus.FAILED,
            'canceled': BuildStatus.CANCELLED,
            'skipped': BuildStatus.SKIPPED
        }
        return status_map.get(status, BuildStatus.PENDING)

    def _fetch_jenkins_pipelines(self, limit: int) -> List[Pipeline]:
        """Fetch pipelines from Jenkins"""
        if not self.jenkins_credentials:
            return []

        try:
            jenkins_url = self.jenkins_credentials['url']
            username = self.jenkins_credentials['username']
            token = self.jenkins_credentials['token']

            # Fetch builds
            api_url = f"{jenkins_url}/api/json"
            response = requests.get(
                api_url,
                auth=(username, token),
                params={'tree': f'jobs[name,builds[number,result,timestamp,duration]{{0,{limit}}}]'}
            )

            if response.status_code != 200:
                return []

            data = response.json()
            pipelines = []

            for job in data.get('jobs', []):
                for build in job.get('builds', [])[:limit]:
                    pipeline = Pipeline(
                        id=f"{job['name']}-{build['number']}",
                        name=f"{job['name']} #{build['number']}",
                        platform=CICDPlatform.JENKINS,
                        branch='',
                        commit_sha='',
                        commit_message='',
                        status=self._map_jenkins_status(build.get('result')),
                        started_at=datetime.fromtimestamp(build['timestamp'] / 1000) if build.get('timestamp') else None,
                        web_url=f"{jenkins_url}/job/{job['name']}/{build['number']}"
                    )

                    pipelines.append(pipeline)
                    self.pipelines[pipeline.id] = pipeline

            return pipelines

        except Exception as e:
            print(f"Error fetching Jenkins pipelines: {e}")
            return []

    def _map_jenkins_status(self, result: Optional[str]) -> BuildStatus:
        """Map Jenkins status to BuildStatus"""
        if result is None:
            return BuildStatus.RUNNING

        status_map = {
            'SUCCESS': BuildStatus.SUCCESS,
            'FAILURE': BuildStatus.FAILED,
            'ABORTED': BuildStatus.CANCELLED,
            'UNSTABLE': BuildStatus.FAILED
        }
        return status_map.get(result, BuildStatus.PENDING)

    def trigger_pipeline(self, branch: str = "main") -> Optional[Pipeline]:
        """
        Trigger a new pipeline

        Args:
            branch: Branch to build

        Returns:
            Pipeline object if successful
        """
        platform = self.configuration.platform

        if platform == CICDPlatform.GITHUB_ACTIONS:
            return self._trigger_github_pipeline(branch)
        elif platform == CICDPlatform.GITLAB_CI:
            return self._trigger_gitlab_pipeline(branch)
        elif platform == CICDPlatform.JENKINS:
            return self._trigger_jenkins_pipeline(branch)

        return None

    def _trigger_github_pipeline(self, branch: str) -> Optional[Pipeline]:
        """Trigger GitHub Actions workflow"""
        # GitHub Actions workflows are triggered by git push
        # This would require creating a workflow_dispatch event
        return None

    def _trigger_gitlab_pipeline(self, branch: str) -> Optional[Pipeline]:
        """Trigger GitLab CI pipeline"""
        if not self.gitlab_token:
            return None

        try:
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                cwd=str(self.project_path),
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return None

            remote_url = result.stdout.strip()
            project_match = re.search(r'gitlab\.com[:/](.+?)(?:\.git)?$', remote_url)
            if not project_match:
                return None

            project_path = project_match.group(1)
            project_id = project_path.replace('/', '%2F')

            api_url = f'https://gitlab.com/api/v4/projects/{project_id}/pipeline'
            headers = {
                'PRIVATE-TOKEN': self.gitlab_token,
                'Content-Type': 'application/json'
            }

            response = requests.post(
                api_url,
                headers=headers,
                json={'ref': branch}
            )

            if response.status_code == 201:
                data = response.json()
                pipeline = Pipeline(
                    id=str(data['id']),
                    name=f"Pipeline #{data['id']}",
                    platform=CICDPlatform.GITLAB_CI,
                    branch=branch,
                    commit_sha=data['sha'],
                    commit_message='',
                    status=BuildStatus.PENDING,
                    web_url=data['web_url']
                )

                self.pipelines[pipeline.id] = pipeline
                self.pipeline_created.emit(pipeline)
                return pipeline

        except Exception as e:
            print(f"Error triggering GitLab pipeline: {e}")

        return None

    def _trigger_jenkins_pipeline(self, branch: str) -> Optional[Pipeline]:
        """Trigger Jenkins build"""
        # Would require Jenkins API call to trigger build
        return None

    def start_monitoring(self, interval_seconds: int = 30):
        """
        Start monitoring pipeline status

        Args:
            interval_seconds: Polling interval
        """
        self.monitoring_enabled = True
        self.monitoring_timer.start(interval_seconds * 1000)

    def stop_monitoring(self):
        """Stop monitoring pipeline status"""
        self.monitoring_enabled = False
        self.monitoring_timer.stop()

    def _check_pipeline_status(self):
        """Check status of running pipelines"""
        if not self.monitoring_enabled:
            return

        # Fetch latest pipeline statuses
        self.fetch_pipelines(limit=5)

    def cancel_pipeline(self, pipeline_id: str) -> bool:
        """Cancel a running pipeline"""
        if pipeline_id not in self.pipelines:
            return False

        pipeline = self.pipelines[pipeline_id]

        # Platform-specific cancellation
        # Would require API calls to cancel

        return False

    def get_pipeline_logs(self, pipeline_id: str) -> str:
        """Get logs for a pipeline"""
        if pipeline_id not in self.pipelines:
            return ""

        # Would require fetching logs from platform API
        return ""

    def get_build_artifacts(self, pipeline_id: str) -> List[str]:
        """Get build artifacts for a pipeline"""
        if pipeline_id not in self.pipelines:
            return []

        pipeline = self.pipelines[pipeline_id]
        artifacts = []

        for job in pipeline.jobs:
            artifacts.extend(job.artifacts)

        return artifacts
