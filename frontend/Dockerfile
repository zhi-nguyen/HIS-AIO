# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the application
# Use npm run build if you have a build script, otherwise for dev just copy
# RUN npm run build

# Production stage (or Dev stage for now)
FROM node:20-alpine

WORKDIR /app

# Copy from builder
COPY --from=builder /app /app

# Expose port
EXPOSE 3000

# Start command
# Adjust this based on your package.json scripts (e.g., 'dev', 'start')
CMD ["npm", "run", "dev"]
