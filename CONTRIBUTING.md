# Contributing to LocalServers

Thank you for your interest in contributing to LocalServers! 🎉

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- macOS version and Python version
- Any relevant error messages

### Suggesting Features

Feature requests are welcome! Please:
- Check if the feature is already requested
- Describe the use case clearly
- Explain why it would be useful

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow the existing code style
   - Keep changes focused and atomic
   - Test your changes thoroughly

4. **Commit your changes**
   ```bash
   git commit -m "Add feature: brief description"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**
   - Provide a clear description of the changes
   - Reference any related issues
   - Include screenshots if UI changes are involved

## Development Setup

```bash
# Clone the repo
git clone https://github.com/Nachx639/localservers.git
cd localservers

# Install dependencies
pip3 install rumps pyobjc --break-system-packages

# Run the app
python3 local_servers.py
```

## Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings for new functions
- Keep functions focused and small

## Testing

Before submitting a PR:
- [ ] Test on a clean macOS environment
- [ ] Verify all existing features still work
- [ ] Test with multiple server types
- [ ] Test with Docker (if applicable)
- [ ] Check for any Python errors or warnings

## Adding New Server Types

To add support for a new server type:

1. Update `identify_server_type()` in `local_servers.py`
2. Add the category to `category_names` in `update_menu()`
3. Test detection with an actual server running
4. Update README.md to mention the new support

Example:
```python
# In identify_server_type()
elif 'myserver' in command_lower:
    return ('MyServer', 'myserver')

# In category_names dict
'myserver': 'MyServer',
```

## Need Help?

Feel free to:
- Open an issue with questions
- Ask in the Pull Request discussion
- Reach out to [@Nachx639](https://github.com/Nachx639)

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow

Thank you for contributing! 🙌
