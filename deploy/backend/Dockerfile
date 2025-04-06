FROM golang:alpine AS builder

WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . ./
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o backend .
FROM alpine:latest
WORKDIR /root
COPY --from=builder /src/backend .
EXPOSE 8080
CMD ["./backend"]
