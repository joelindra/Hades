# HADES - Security Framework From HELL v7.1

<p align="center">
  <img src="https://img.shields.io/badge/Version-7-blue.svg" alt="Version">
  <img src="https://img.shields.io/badge/Platform-Linux-green.svg" alt="Platform">
  <img src="https://img.shields.io/badge/Shell-Bash-orange.svg" alt="Shell">
  <img src="https://img.shields.io/badge/License-MIT-red.svg" alt="License">
</p>

<p align="center">
  <strong>A comprehensive automated bug bounty framework for reconnaissance, vulnerability assessment, and security testing</strong>
</p>

---

<img width="323" height="450" alt="image" src="https://github.com/user-attachments/assets/afe134a6-8a11-4f6f-8d7c-79407253e7de" />

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Modules](#modules)
- [Requirements](#requirements)
- [Examples](#examples)
- [Contributing](#contributing)
- [Disclaimer](#disclaimer)
- [Author](#author)

---

## 🎯 Overview

HADES is an advanced bug bounty framework designed to automate reconnaissance, vulnerability scanning, and security testing processes. Built with efficiency and comprehensive coverage in mind, it integrates multiple industry-standard tools to provide a unified platform for security researchers and bug bounty hunters.

### Key Highlights
- **Automated Reconnaissance**: Mass and single target reconnaissance
- **Vulnerability Assessment**: SQL injection, XSS, LFI testing
- **OWASP Testing**: Client-side and cryptography testing
- **Special Operations**: Subdomain takeover, CORS/CSRF testing
- **Elegant Interface**: Color-coded output with progress indicators

---

## ✨ Features

### 🔍 Reconnaissance Capabilities
- **Mass Target Recon**: Automated subdomain enumeration and probing
- **Single Target Recon**: Focused reconnaissance on specific targets
- **Port Scanning**: Comprehensive port discovery and service enumeration

### 🛡️ Vulnerability Testing
- **SQL Injection**: Automated SQLi detection and exploitation
- **Cross-Site Scripting (XSS)**: DOM and reflected XSS testing
- **Local File Inclusion (LFI)**: Path traversal and file disclosure testing

### 🚀 Advanced Security Testing
- **Subdomain Takeover**: Detection of vulnerable subdomains
- **CORS Misconfiguration**: Cross-origin resource sharing testing
- **CSRF Testing**: Cross-site request forgery vulnerability assessment
- **Directory Brute-forcing**: Hidden directory and file discovery
- **JavaScript Analysis**: Secret and sensitive data extraction from JS files

### 🔐 OWASP Testing Framework
- **Client-side Testing**: Browser-based vulnerability assessment
- **Cryptography Testing**: SSL/TLS and encryption analysis

---

## 🔧 Installation

### Prerequisites
- Linux/Unix-based operating system
- Root privileges (required for certain operations)
- Internet connection for tool installation

### Quick Install
```bash
# Clone the repository
git clone https://github.com/joelindra/hades.git

# Navigate to directory
cd hades

# Make executable
chmod +x hades

# Install dependencies
sudo ./hades --install
```

### Manual Installation
If you prefer to install dependencies manually, ensure you have the following tools:
- `wafw00f`, `subfinder`, `assetfinder`, `httprobe`
- `waybackurls`, `anew`, `ffuf`, `gf`
- `nmap`, `nuclei`, `subjack`, `dirsearch`
- `sqltimer`, `dalfox`, `trufflehog`
- `sslscan`, `openssl`, `curl`, `jq`

---

## 🚀 Usage

### Basic Syntax
```bash
./hades [OPTIONS]
```

### Display Help
```bash
./hades --help
```

---

## 📦 Modules

### 🔍 Reconnaissance
| Command | Description | Tools Used |
|---------|-------------|------------|
| `-d, --mass-recon` | Mass Target Reconnaissance | wafw00f, subfinder, assetfinder, httprobe, waybackurls, anew, ffuf, gf, curl |
| `-s, --single-recon` | Single Target Reconnaissance | wafw00f, waybackurls, anew, ffuf, gf, curl |
| `-f, --port-scan` | Port Scanning | nmap, curl |

### 🛡️ Injection Testing
| Command | Description | Tools Used |
|---------|-------------|------------|
| `-p, --mass-sql` | Mass SQL Injection Testing | wafw00f, subfinder, assetfinder, httprobe, waybackurls, anew, ffuf, gf, sqltimer, curl |
| `-o, --single-sql` | Single Target SQL Injection | wafw00f, waybackurls, anew, ffuf, gf, sqltimer, curl |
| `-w, --mass-xss` | Mass XSS Testing | wafw00f, subfinder, assetfinder, httprobe, waybackurls, anew, ffuf, gf, dalfox, curl |
| `-x, --single-xss` | Single Target XSS Testing | wafw00f, waybackurls, anew, ffuf, gf, dalfox, curl |
| `-n, --single-lfi` | Local File Inclusion Testing | wafw00f, waybackurls, anew, ffuf, gf, mapfile, md5sum, curl |

### 🎯 Special Operations
| Command | Description | Tools Used |
|---------|-------------|------------|
| `-m, --mass-assess` | Mass Vulnerability Assessment | wafw00f, subfinder, assetfinder, httprobe, nuclei, curl |
| `-y, --sub-takeover` | Subdomain Takeover Testing | wafw00f, notifier.sh, subfinder, assetfinder, httprobe, subjack, curl |
| `-q, --dir-patrol` | Directory Brute-forcing | wafw00f, notifier.sh, subfinder, assetfinder, httprobe, dirsearch |
| `-l, --js-finder` | JavaScript Secret Analysis | wafw00f, notifier.sh, subfinder, assetfinder, httprobe, waybackurls, anew, trufflehog, curl |
| `-k, --mass-cors` | CORS Misconfiguration Testing | wafw00f, subfinder, assetfinder, httprobe, waybackurls, anew, ffuf, gf |
| `-u, --mass-csrf` | CSRF Vulnerability Testing | wafw00f, subfinder, assetfinder, httprobe, waybackurls, anew, ffuf, gf, curl |

### 🔐 OWASP Testing
| Command | Description | Tools Used |
|---------|-------------|------------|
| `-e, --client-test` | Client-side Testing | curl, jq |
| `-b, --weak-test` | Cryptography Testing | nmap, sslscan, openssl, curl, timeout |

### ⚙️ System
| Command | Description |
|---------|-------------|
| `-i, --install` | Install Dependencies |
| `-h, --help` | Display Help Menu |

---

## 📋 Requirements

### System Requirements
- **OS**: Kali Linux
- **RAM**: Minimum 2GB, Recommended 4GB+
- **Storage**: At least 5GB free space
- **Network**: Stable internet connection

### Tool Dependencies
The framework automatically installs required tools, but manual installation may be needed for:
- Go-based tools (subfinder, assetfinder, httprobe, anew, ffuf, nuclei)
- Python-based tools (wafw00f, dirsearch, trufflehog)
- System tools (nmap, curl, openssl, sslscan)

---

## 💡 Examples

### Basic Reconnaissance
```bash
# Single target reconnaissance
./hades --single-recon

# Mass target reconnaissance  
./hades --mass-recon

# Port scanning
./hades --port-scan
```

### Vulnerability Testing
```bash
# SQL injection testing
./hades --single-sql

# XSS vulnerability testing
./hades --mass-xss

# LFI testing
./hades --single-lfi
```

### Advanced Testing
```bash
# Subdomain takeover testing
./hades --sub-takeover

# CORS misconfiguration testing
./hades --mass-cors

# JavaScript secret analysis
./hades --js-finder
```

### OWASP Testing
```bash
# Client-side testing
./hades --client-test

# Cryptography testing
./hades --weak-test
```

### Multiple Operations
```bash
# Combine multiple modules
./hades --mass-recon --mass-sql --sub-takeover
```

---

## 🤝 Contributing

We welcome contributions from the security community! Here's how you can help:

### Ways to Contribute
- **Bug Reports**: Report issues and bugs
- **Feature Requests**: Suggest new features or improvements
- **Code Contributions**: Submit pull requests with enhancements
- **Documentation**: Improve documentation and examples
- **Tool Integration**: Add support for new security tools

### Development Guidelines
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Standards
- Follow bash scripting best practices
- Maintain consistent code formatting
- Add comments for complex functions
- Test thoroughly before submission

---

## ⚠️ Disclaimer

### Legal Notice
This tool is intended for **authorized security testing only**. Users are responsible for:

- **Legal Compliance**: Ensure you have proper authorization before testing any target
- **Ethical Usage**: Use only for legitimate security research and bug bounty programs
- **Responsible Disclosure**: Follow responsible disclosure practices for any vulnerabilities found

### Important Notes
- **Authorization Required**: Never use this tool against systems you don't own or have explicit permission to test
- **Educational Purpose**: This tool is for educational and authorized testing purposes only
- **No Warranty**: The tool is provided "as-is" without any warranty
- **User Responsibility**: Users are solely responsible for their actions and any consequences

### Compliance
By using HADES, you agree to:
- Comply with all applicable laws and regulations
- Respect target systems and avoid causing damage
- Use the tool ethically and responsibly
- Follow bug bounty program rules and guidelines

---

## 👨‍💻 Author

**Joel Indra (Anonre)**
- GitHub: [@joelindra](https://github.com/joelindra)
---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Special thanks to the creators and maintainers of the integrated security tools that make HADES possible:
- Tom Hudson (tomnomnom) - for various Go-based tools
- OWASP Community - for security testing methodologies
- Bug bounty community - for continuous feedback and improvements

---

## 📞 Support

### Getting Help
- **Issues**: Report bugs and issues on [GitHub Issues](https://github.com/joelindra/hades/issues)
- **Discussions**: Join discussions on [GitHub Discussions](https://github.com/joelindra/hades/discussions)
- **Documentation**: Check the [Wiki](https://github.com/joelindra/hades/wiki) for detailed guides

### Community
- Follow the project for updates
- Star the repository if you find it useful
- Share with the security community

---

![image](https://github.com/user-attachments/assets/bf2fdec0-8e1a-4f2b-86ce-68c938ef0b22)

---
<p align="center">
  <sub>⚡ Happy Hunting! ⚡</sub>
</p>
