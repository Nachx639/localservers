#!/usr/bin/env python3
"""
LocalServers - Menubar app to monitor local servers and tunnels
"""

import rumps
import subprocess
import re
import json
import os
from pathlib import Path

class LocalServersApp(rumps.App):
    def __init__(self):
        super(LocalServersApp, self).__init__("🌐", quit_button=None)

        # Config file
        self.config_file = os.path.expanduser("~/.localservers.json")
        self.load_preferences()

        # Managed servers
        self.managed_servers = self.prefs.get('managed_servers', {})

        self.menu = ["Refresh", "---"]
        self.timer = rumps.Timer(self.update_menu, 5)
        self.timer.start()
        self.update_menu(None)

    def load_preferences(self):
        """Load user preferences from config file"""
        defaults = {
            'show_categories': {},  # Dynamic: category -> bool
            'managed_servers': {}    # port -> {dir, command, name}
        }

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.prefs = {**defaults, **json.load(f)}
            except:
                self.prefs = defaults
        else:
            self.prefs = defaults

    def save_preferences(self):
        """Save preferences to config file"""
        self.prefs['managed_servers'] = self.managed_servers
        with open(self.config_file, 'w') as f:
            json.dump(self.prefs, f, indent=2)

    def detect_servers(self):
        """Detect local servers using lsof"""
        servers = []
        categories_found = set()

        try:
            result = subprocess.run(
                ['lsof', '-iTCP', '-sTCP:LISTEN', '-nP'],
                capture_output=True,
                text=True,
                timeout=3
            )

            ports = {}
            for line in result.stdout.split('\n')[1:]:
                if not line.strip():
                    continue

                parts = line.split()
                if len(parts) < 9:
                    continue

                command = parts[0]
                pid = parts[1]
                address = parts[8]

                port_match = re.search(r':(\d+)$', address)
                if port_match:
                    port = int(port_match.group(1))

                    # Skip system ports
                    if port < 1000:
                        continue

                    if port not in ports:
                        server_type, category = self.identify_server_type(command, port)
                        categories_found.add(category)

                        # Check if should show based on category filter
                        if not self.should_show_category(category):
                            continue

                        # Check if it's a managed server
                        is_managed = str(port) in self.managed_servers

                        # Detect if running from launchd/plist vs terminal
                        is_service = self.is_launchd_service(pid)

                        ports[port] = {
                            'port': port,
                            'type': server_type,
                            'category': category,
                            'command': command,
                            'pid': pid,
                            'managed': is_managed,
                            'is_service': is_service
                        }

            servers = sorted(ports.values(), key=lambda x: x['port'])

        except Exception as e:
            pass

        return servers, categories_found

    def is_launchd_service(self, pid):
        """Check if process is running from launchd (plist service)"""
        try:
            current_pid = str(pid)
            max_depth = 20  # Avoid infinite loops

            for _ in range(max_depth):
                # Get parent process ID
                result = subprocess.run(
                    ['ps', '-o', 'ppid=', '-p', current_pid],
                    capture_output=True,
                    text=True,
                    timeout=1
                )

                ppid = result.stdout.strip()
                if not ppid or ppid == '0':
                    return False

                # Found launchd!
                if ppid == '1':
                    return True

                # Check if parent command contains launchd
                parent_result = subprocess.run(
                    ['ps', '-o', 'comm=', '-p', ppid],
                    capture_output=True,
                    text=True,
                    timeout=1
                )

                parent_comm = parent_result.stdout.strip().lower()
                if 'launchd' in parent_comm:
                    return True

                # Move up the chain
                current_pid = ppid

            # Additional check: look for LaunchAgent or LaunchDaemon in process environment
            env_result = subprocess.run(
                ['ps', 'eww', '-p', str(pid)],
                capture_output=True,
                text=True,
                timeout=1
            )

            if 'LaunchAgent' in env_result.stdout or 'LaunchDaemon' in env_result.stdout:
                return True

        except:
            pass

        return False

    def identify_server_type(self, command, port):
        """Identify server type and category"""
        command_lower = command.lower()

        # Next.js (common dev ports)
        if 'node' in command_lower:
            if port in [3000, 3001]:
                return ('Next.js', 'nextjs')
            else:
                return ('Node.js', 'node')

        # Python
        elif 'python' in command_lower:
            return ('Python', 'python')

        # Ruby/Rails
        elif 'ruby' in command_lower or 'rails' in command_lower:
            return ('Ruby', 'ruby')

        # Rust
        elif 'cargo' in command_lower or 'rust' in command_lower:
            return ('Rust', 'rust')

        # Go
        elif command_lower.startswith('go'):
            return ('Go', 'go')

        # Electron
        elif 'electron' in command_lower or 'controlco' in command_lower:
            return ('Electron', 'electron')

        # Java
        elif 'java' in command_lower:
            return ('Java', 'java')

        # Others
        else:
            return (command[:20], 'other')

    def should_show_category(self, category):
        """Check if category should be shown (defaults to True for all)"""
        return self.prefs.get('show_categories', {}).get(category, True)

    def detect_tunnels(self):
        """Detect active tunnels with proper hostname and port mapping"""
        tunnels = {}

        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=3
            )

            for line in result.stdout.split('\n'):
                # Cloudflare tunnels
                if 'cloudflared tunnel' in line and 'run' in line:
                    tunnel_name_match = re.search(r'run\s+(\S+)', line)
                    tunnel_id_or_name = tunnel_name_match.group(1) if tunnel_name_match else None

                    # Find config file
                    config_match = re.search(r'--config\s+(\S+)', line)
                    config_paths = []

                    if config_match:
                        config_paths.append(os.path.expanduser(config_match.group(1)))
                    else:
                        config_paths.append(os.path.expanduser('~/.cloudflared/config.yml'))

                    for config_path in config_paths:
                        if not os.path.exists(config_path):
                            continue

                        try:
                            with open(config_path, 'r') as f:
                                config_content = f.read()

                                ingress_pattern = r'- hostname:\s*(\S+)\s+service:\s*http://(?:localhost|127\.0\.0\.1):(\d+)'
                                ingress_matches = re.findall(ingress_pattern, config_content)

                                for hostname, port in ingress_matches:
                                    if 'http_status' in hostname:
                                        continue

                                    tunnels[hostname] = {
                                        'type': 'Cloudflare',
                                        'hostname': hostname,
                                        'port': port,
                                        'display': f"{hostname} → :{port}"
                                    }
                        except:
                            pass

                # Tailscale funnel - generic detection
                elif 'tailscale' in line and 'funnel' in line:
                    port_match = re.search(r'funnel\s+(\d+)', line)
                    port = port_match.group(1) if port_match else 'unknown'

                    # Try to get actual Tailscale hostname
                    try:
                        ts_status = subprocess.run(
                            ['tailscale', 'status', '--json'],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        if ts_status.returncode == 0:
                            ts_data = json.loads(ts_status.stdout)
                            hostname = ts_data.get('Self', {}).get('DNSName', '').rstrip('.')
                        else:
                            hostname = 'tailscale-device'
                    except:
                        hostname = 'tailscale-device'

                    key = f'tailscale-{port}'
                    if key not in tunnels:
                        tunnels[key] = {
                            'type': 'Tailscale Funnel',
                            'hostname': hostname,
                            'port': port,
                            'display': f"{hostname}:{port}"
                        }

        except Exception as e:
            pass

        return list(tunnels.values())

    def detect_project_type(self, directory):
        """Auto-detect project type and suggest start command"""
        directory = Path(directory)

        # Node.js / Next.js
        if (directory / 'package.json').exists():
            try:
                with open(directory / 'package.json', 'r') as f:
                    package = json.load(f)

                    # Next.js
                    if 'next' in package.get('dependencies', {}) or 'next' in package.get('devDependencies', {}):
                        return ('Next.js', 'npm run dev')

                    # Generic Node
                    scripts = package.get('scripts', {})
                    if 'dev' in scripts:
                        return ('Node.js', 'npm run dev')
                    elif 'start' in scripts:
                        return ('Node.js', 'npm start')
            except:
                pass
            return ('Node.js', 'npm start')

        # Python
        if (directory / 'requirements.txt').exists() or (directory / 'pyproject.toml').exists():
            if (directory / 'manage.py').exists():
                return ('Django', 'python manage.py runserver')
            elif (directory / 'app.py').exists():
                return ('Flask', 'python app.py')
            return ('Python', 'python main.py')

        # Rust
        if (directory / 'Cargo.toml').exists():
            return ('Rust', 'cargo run')

        # Go
        if (directory / 'go.mod').exists():
            return ('Go', 'go run .')

        # Ruby
        if (directory / 'Gemfile').exists():
            return ('Ruby/Rails', 'rails server')

        return (None, None)

    @rumps.clicked("Refresh")
    def refresh(self, _):
        """Manual refresh"""
        self.update_menu(None)

    def add_server_dialog(self, _):
        """Show dialog to add a new server"""
        # Use AppleScript to show folder picker
        try:
            result = subprocess.run(
                ['osascript', '-e', 'POSIX path of (choose folder with prompt "Select your project directory:")'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                # User cancelled
                return

            directory = result.stdout.strip()

            if not directory or not os.path.isdir(directory):
                rumps.alert("Error", "Invalid directory")
                return

            # Detect project type
            project_type, suggested_command = self.detect_project_type(directory)

            if not project_type:
                rumps.alert("Unknown Project", "Could not detect project type. Add manually via terminal.")
                return

            # Ask for port
            port_window = rumps.Window(
                message=f"Detected: {project_type}\nCommand: {suggested_command}\n\nEnter port number:",
                title="Configure Server",
                default_text="3000",
                ok="Add",
                cancel="Cancel",
                dimensions=(320, 24)
            )

            port_response = port_window.run()

            if port_response.clicked:
                port = port_response.text.strip()

                # Save to managed servers
                self.managed_servers[port] = {
                    'directory': directory,
                    'command': suggested_command,
                    'type': project_type,
                    'name': Path(directory).name
                }
                self.save_preferences()

                # Start server
                self.start_server(port)

                rumps.alert("Server Added", f"{project_type} on port {port}\nStarting...")
                self.update_menu(None)

        except Exception as e:
            rumps.alert("Error", f"Could not add server: {str(e)}")

    def start_server(self, port):
        """Start a managed server"""
        if port not in self.managed_servers:
            return

        server = self.managed_servers[port]
        directory = server['directory']
        command = server['command']

        # Start in background
        subprocess.Popen(
            command,
            shell=True,
            cwd=directory,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def stop_server(self, sender):
        """Stop a server by killing its PID"""
        port = sender._port
        pid = sender._pid

        try:
            subprocess.run(['kill', str(pid)])
            rumps.notification("Server Stopped", f"Stopped server on port {port}", "")
            self.update_menu(None)
        except:
            rumps.alert("Error", "Could not stop server")

    def restart_server(self, sender):
        """Restart a server"""
        port = sender._port
        pid = sender._pid

        # Stop
        try:
            subprocess.run(['kill', str(pid)])
        except:
            pass

        # Wait a bit
        import time
        time.sleep(1)

        # Start if managed
        if str(port) in self.managed_servers:
            self.start_server(str(port))
            rumps.notification("Server Restarted", f"Restarted server on port {port}", "")

        self.update_menu(None)

    def copy_url(self, sender):
        """Copy localhost URL to clipboard"""
        port = sender._port
        url = f"http://localhost:{port}"

        subprocess.run(['pbcopy'], input=url.encode(), check=True)
        rumps.notification("URL Copied", url, "")

    def copy_tunnel_url(self, sender):
        """Copy tunnel URL to clipboard"""
        hostname = sender._hostname
        url = f"https://{hostname}"

        subprocess.run(['pbcopy'], input=url.encode(), check=True)
        rumps.notification("URL Copied", url, "")

    def restart_cloudflare_tunnel(self, sender):
        """Restart Cloudflare tunnel"""
        hostname = sender._hostname

        # Find the cloudflared process for this tunnel
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=3
            )

            pid = None
            for line in result.stdout.split('\n'):
                if 'cloudflared tunnel' in line and 'run' in line:
                    # Check if this process handles this hostname
                    config_match = re.search(r'--config\s+(\S+)', line)
                    config_path = None

                    if config_match:
                        config_path = os.path.expanduser(config_match.group(1))
                    else:
                        config_path = os.path.expanduser('~/.cloudflared/config.yml')

                    if config_path and os.path.exists(config_path):
                        with open(config_path, 'r') as f:
                            if hostname in f.read():
                                parts = line.split()
                                pid = parts[1]
                                break

            if pid:
                # Kill process
                subprocess.run(['kill', pid])

                # Wait a bit
                import time
                time.sleep(2)

                # Restart tunnel (need to find the original command)
                # This is tricky - for now just notify user
                rumps.notification(
                    "Tunnel Stopped",
                    f"Stopped tunnel for {hostname}. Restart manually with: cloudflared tunnel run",
                    ""
                )
            else:
                rumps.alert("Error", "Could not find tunnel process")

        except Exception as e:
            rumps.alert("Error", f"Could not restart tunnel: {str(e)}")

    def toggle_category_filter(self, sender):
        """Toggle category visibility"""
        category = sender._category

        current = self.prefs.get('show_categories', {}).get(category, True)
        self.prefs.setdefault('show_categories', {})[category] = not current

        sender.state = not current
        self.save_preferences()
        self.update_menu(None)

    def update_menu(self, sender):
        """Update menu with servers and tunnels"""
        servers, categories_found = self.detect_servers()
        tunnels = self.detect_tunnels()

        menu_items = []

        # Add server button
        menu_items.append(rumps.MenuItem("➕ Add Server", callback=self.add_server_dialog))
        menu_items.append("---")

        # Legend
        legend_menu = rumps.MenuItem("📖 Legend")
        legend_menu.add("⚙️  = Service (plist/launchd)")
        legend_menu.add("💻 = Terminal process")
        legend_menu.add("⭐ = Managed by LocalServers")
        menu_items.append(legend_menu)
        menu_items.append("---")

        # Servers section
        if servers:
            menu_items.append(f"📡 Servers ({len(servers)})")
            for server in servers:
                port = server['port']
                server_type = server['type']
                pid = server['pid']
                managed = server['managed']
                is_service = server.get('is_service', False)

                # Main item with badges
                badges = []
                if is_service:
                    badges.append("⚙️")  # Service/plist
                else:
                    badges.append("💻")  # Terminal

                if managed:
                    badges.append("⭐")  # Managed by LocalServers

                badge_str = " ".join(badges)
                main_label = f"  {badge_str} localhost:{port} ({server_type})"

                server_item = rumps.MenuItem(main_label)

                # Submenu with actions
                open_item = rumps.MenuItem("Open in Browser", callback=lambda s, p=port: self.open_localhost(p))
                copy_item = rumps.MenuItem("Copy URL", callback=self.copy_url)
                copy_item._port = port

                restart_item = rumps.MenuItem("Restart", callback=self.restart_server)
                restart_item._port = port
                restart_item._pid = pid

                stop_item = rumps.MenuItem("Stop", callback=self.stop_server)
                stop_item._port = port
                stop_item._pid = pid

                server_item.add(open_item)
                server_item.add(copy_item)
                server_item.add("---")
                server_item.add(restart_item)
                server_item.add(stop_item)

                menu_items.append(server_item)
        else:
            menu_items.append("📡 No servers running")

        menu_items.append("---")

        # Tunnels section
        if tunnels:
            menu_items.append(f"🚇 Tunnels ({len(tunnels)})")
            for tunnel in tunnels:
                tunnel_item = rumps.MenuItem(f"  {tunnel['display']}")

                # Submenu with actions
                open_tunnel = rumps.MenuItem(
                    "Open in Browser",
                    callback=lambda s, h=tunnel['hostname']: subprocess.run(['open', f"https://{h}"])
                )
                copy_tunnel = rumps.MenuItem("Copy URL", callback=self.copy_tunnel_url)
                copy_tunnel._hostname = tunnel['hostname']

                # Restart tunnel (only for managed/known tunnels)
                if tunnel['type'] == 'Cloudflare':
                    restart_tunnel = rumps.MenuItem("Restart Tunnel", callback=self.restart_cloudflare_tunnel)
                    restart_tunnel._hostname = tunnel['hostname']
                    restart_tunnel._port = tunnel['port']

                    tunnel_item.add(open_tunnel)
                    tunnel_item.add(copy_tunnel)
                    tunnel_item.add("---")
                    tunnel_item.add(restart_tunnel)
                else:
                    tunnel_item.add(open_tunnel)
                    tunnel_item.add(copy_tunnel)

                menu_items.append(tunnel_item)
        else:
            menu_items.append("🚇 No tunnels active")

        menu_items.append("---")

        # Dynamic filters based on categories found
        if categories_found:
            filters_menu = rumps.MenuItem("⚙️ Filters")

            # Map categories to display names
            category_names = {
                'nextjs': 'Next.js',
                'node': 'Node.js',
                'python': 'Python',
                'ruby': 'Ruby',
                'rust': 'Rust',
                'go': 'Go',
                'java': 'Java',
                'electron': 'Electron',
                'other': 'Other'
            }

            for category in sorted(categories_found):
                display_name = category_names.get(category, category.title())
                item = rumps.MenuItem(
                    f"Show {display_name}",
                    callback=self.toggle_category_filter
                )
                item._category = category
                item.state = self.should_show_category(category)
                filters_menu.add(item)

            menu_items.append(filters_menu)

        menu_items.append("Refresh")
        menu_items.append("---")
        menu_items.append(rumps.MenuItem("Quit", callback=rumps.quit_application))

        # Update menu
        self.menu.clear()
        for item in menu_items:
            self.menu.add(item)

        # Update icon
        total = len(servers)
        if total > 0:
            self.title = f"🌐 {total}"
        else:
            self.title = "🌐"

    def open_localhost(self, port):
        """Open localhost:port in browser"""
        subprocess.run(['open', f'http://localhost:{port}'])

if __name__ == "__main__":
    LocalServersApp().run()
