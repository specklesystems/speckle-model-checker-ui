# Build stage
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copy go mod and sum files
COPY go.mod ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -o main ./cmd/main.go

# Final stage
FROM alpine:latest

WORKDIR /app

# Copy the binary from builder
COPY --from=builder /app/main .

# Copy frontend files
COPY frontend/templates ./frontend/templates
COPY frontend/static ./frontend/static

# Copy Firebase credentials
COPY firebase-service-account-key.json .

# Expose port
EXPOSE 8080

# Run the application
CMD ["./main"] 