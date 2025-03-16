# ChatMemoryAPI

This repository is the code of my API that manage chat history memory for my chatbot applications. Made in FastAPI and deployed on AWS, that API send data to a postgres database on RDS (also hosted on AWS).

## Overview

ChatMemoryAPI is a simple yet powerful solution for managing chat history for chatbot applications. It provides endpoints to store, retrieve, and manage conversation data efficiently.

## Technical Stack

- **Backend**: Built with FastAPI, a modern Python web framework that offers high performance and easy-to-write API endpoints
- **Database**: PostgreSQL on AWS RDS for reliable and scalable data storage
- **Deployment**: Hosted on AWS for high availability and scalability

## API Structure

The API is organized around RESTful principles with endpoints for:
- Creating new chat sessions
- Storing messages in existing conversations
- Retrieving conversation history
- Managing user data and preferences

## Database Schema

The database is structured with the following main tables:
- `users`: Stores user information
- `conversations`: Tracks individual chat sessions
- `messages`: Contains the actual chat messages with timestamps and metadata
- `settings`: Stores configuration options for different chat experiences

## Deployment Strategy

1. **CI/CD Pipeline**: Automated deployment using GitHub Actions
2. **Infrastructure**: AWS services including:
   - EC2 for hosting the API
   - RDS for PostgreSQL database
   - Load balancing for high availability
   - CloudWatch for monitoring and logging
3. **Scaling**: Configured to automatically scale based on traffic demands

