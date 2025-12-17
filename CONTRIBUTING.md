# Contributing Guidelines

Thank you for your interest in contributing to this Kubernetes AI Diagnostics Platform! This project welcomes contributions from the community.

## How to Contribute

### Reporting Issues

If you encounter any problems or have suggestions:

1. **Check existing issues** to avoid duplicates
2. **Provide detailed information**:
   - Kubernetes version and cluster configuration
   - Steps to reproduce the issue
   - Expected vs actual behavior
   - Relevant logs and error messages
   - Screenshots if applicable

### Suggesting Enhancements

For feature requests or improvements:

1. **Open an issue** describing the enhancement
2. **Explain the use case** and why it would be valuable
3. **Provide examples** if possible
4. **Be open to discussion** about implementation approaches

### Submitting Pull Requests

1. **Fork the repository** and create a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following these guidelines:
   - Write clear, descriptive commit messages
   - Add comments to complex logic
   - Update documentation if needed
   - Test your changes in a real cluster environment

3. **Ensure code quality**:
   - Python code should follow PEP 8 style guidelines
   - YAML files should be properly indented (2 spaces)
   - Add docstrings to new functions/classes
   - Include error handling where appropriate

4. **Submit your pull request**:
   - Provide a clear description of changes
   - Reference any related issues
   - Include testing steps
   - Be responsive to feedback

## Development Setup

### Prerequisites

- Kubernetes cluster (kubeadm or similar)
- Python 3.10+
- Helm 3
- kubectl configured

### Local Development

```bash
# Clone the repository
git clone https://github.com/aashish-26/Kubernetes-platform-with-AI-powered-incident-diagnostics-.git
cd Kubernetes-platform-with-AI-powered-incident-diagnostics-

# Set up Python virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run AI service locally
export K8S_IN_CLUSTER=false
export PROMETHEUS_URL=http://localhost:9090  # If port-forwarded
uvicorn ai.app:app --host 0.0.0.0 --port 8000
```

## Code Style

### Python
- Use type hints where appropriate
- Follow PEP 8 conventions
- Write descriptive variable and function names
- Keep functions focused and single-purpose
- Add docstrings for modules, classes, and functions

### Kubernetes Manifests
- Use consistent indentation (2 spaces)
- Add comments for complex configurations
- Include resource requests and limits
- Follow security best practices (RBAC, non-root containers)

### Documentation
- Use clear, professional language
- Include examples and use cases
- Update README.md if adding new features
- Add inline comments for complex logic

## Testing

Before submitting:

1. **Functional Testing**:
   - Deploy to a test Kubernetes cluster
   - Verify all endpoints respond correctly
   - Test with real failure scenarios

2. **Documentation Testing**:
   - Ensure runbooks are accurate
   - Verify all commands execute successfully
   - Check that screenshots match current UI

3. **Integration Testing**:
   - Test with different Kubernetes versions if possible
   - Verify Prometheus metrics collection
   - Confirm Grafana dashboards load correctly

## Questions?

If you have questions about contributing:
- Open a discussion in the GitHub repository
- Check existing documentation in the docs/ folder
- Review the Architecture.md for system design context

## Code of Conduct

This project follows standard open-source etiquette:
- Be respectful and professional
- Provide constructive feedback
- Focus on the technical merits
- Welcome diverse perspectives
- Help others learn and grow

## Recognition

All contributors will be acknowledged in the project. Significant contributions may be highlighted in release notes.

---

Thank you for helping improve this project! 🚀
