# HIS-AIO (Hospital Information System - All In One)

## The Problem (Pain Points)

Modern healthcare facilities often struggle with **fragmented information systems**. Medical staff face several critical pain points daily:

- **Data Silos**: Patient records, laboratory results (LIS), radiology images (RIS), and pharmacy inventories operate on disconnected platforms.

- **Administrative Burnout**: Doctors and nurses spend an excessive amount of time on manual data entry, writing clinical summaries, and checking drug interactions instead of focusing on patient care.

- **Inefficient Triage & Queuing**: Traditional queue management and reception processes are manual, leading to bottlenecks and inaccurate priority assignments for urgent cases.

---

## The Solution

**HIS-AIO** is an AI-powered, unified hospital management system designed to centralize and automate clinical workflows. We solve the fragmentation problem by integrating core hospital modules into a single ecosystem powered by an advanced AI Engine.

Key features include:

- **Centralized Modules**: A unified architecture combining EMR (Electronic Medical Records), LIS (Laboratory Information System), RIS (Radiology Information System), Pharmacy, and Billing.

- **Multi-Agent AI Ecosystem**: Utilizing specialized AI agents (**Triage Agent**, **Clinical Agent**, **Pharmacist Agent**, and **Paraclinical Agent**) built on LangGraph to assist medical staff in real-time.

- **RAG-Powered Clinical Decision Support (CDSS)**: An integrated Retrieval-Augmented Generation service that cross-references medical guidelines and patient history to suggest diagnoses and flag potential drug interactions.

- **Smart Triage & Queuing**: Automated triage workflows at reception, combined with real-time WebSocket-based queue management (QMS).

---

## The Results

By deploying HIS-AIO, healthcare facilities achieve:

- **Streamlined Workflows**: A seamless journey for the patient from reception and triage to diagnosis, lab testing, and pharmacy dispensation.

- **Enhanced Decision-Making**: Doctors receive instant, AI-backed clinical suggestions and automated summaries, significantly reducing cognitive load and the risk of medical errors.

- **Operational Efficiency**: Reduced waiting times through optimized smart queuing and automated interoperability (FHIR/DICOM) between medical devices and the core system.

---

## Tech Stack Overview

| Layer | Technologies |
|---|---|
| **Frontend** | Next.js, React, TailwindCSS, WebSocket (Socket.io-client) |
| **Backend** | Python, Django, Django REST Framework, Celery, Redis (Caching & Task queues) |
| **AI Engine** | LangChain/LangGraph, RAG Service, Vector Store embeddings |
| **Interoperability** | Orthanc (PACS server/DICOM), FHIR parsers |
| **Infrastructure** | Docker, Docker Compose |

---

## Getting Started

### 1. Prerequisites

Ensure you have **Docker** and **Docker Compose** installed on your local machine.

- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)

### 2. Installation

Clone the repository and start the services using Docker Compose:

```bash
git clone <repository_url>
cd HIS-AIO
docker-compose up -d --build
```

### 3. Initializing the Database

Run the core seed commands to populate the database with initial ICD-10 codes, hospital structures, and standard clinical data:

```bash
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py seed_all
```
