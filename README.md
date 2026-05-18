# HIS-AIO (Hospital Information System All-in-One)

## 🏥 Introduction

HIS-AIO is a comprehensive Hospital Information System designed to streamline healthcare management, medical services, and administrative operations. The system integrates various advanced modules to provide a robust, scalable, and intelligent platform for modern hospitals, bridging the gap between clinical efficiency and advanced technology.

## ✨ Features

- **Core Services**: Centralized management of hospital data, staff administration, and patient records.
- **Medical Services**:
  - **LIS (Laboratory Information System)**: Efficiently manages laboratory tests, tracking, results, and medical reporting.
  - **PACS (Picture Archiving and Communication System)**: A dedicated server to store, retrieve, and distribute medical imaging (e.g., X-rays, MRIs, CT scans).
- **AI Integration**: Features intelligent AI engines, including specialized agents (such as a Pharmacist Agent), to assist medical professionals in accurate decision-making and optimal patient care.
- **Modern Infrastructure**: Fully containerized using Docker, allowing for easy deployment, horizontal scaling, and environment consistency across development and production.

## 🏗️ Project Structure

- `/backend`: The core backend API (powered by Python and Django), handling complex business logic, database ORM operations, AI agent orchestrations, and RESTful/GraphQL endpoints.
- `/frontend`: The interactive user interface designed for hospital staff, system administrators, and doctors to interact with the system efficiently.
- `/pacs_server`: A dedicated subsystem handling medical image processing, archiving, and communication protocols.
- `docker-compose.yml`: The central orchestration configuration for seamless multi-container deployment using Docker.

## 🚀 Getting Started

### Prerequisites

- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)

### Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/zhi-nguyen/HIS-AIO.git
   cd QuanLyBenhVienHIS
   ```

2. **Start the services**:
   Use Docker Compose to build and spin up the entire stack in detached mode:
   ```bash
   docker-compose up --build -d
   ```

3. **Access the application**:
   - The frontend, backend APIs, and PACS services will be exposed on their respectively configured ports (refer to the `docker-compose.yml` for exact port mappings).

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page if you want to contribute.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
