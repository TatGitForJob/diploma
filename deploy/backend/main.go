package main

import (
	"context"
	"log"
	"math/rand"
	"net/http"
	"os"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	"go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.21.0"
)

var (
	requestsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_requests_total",
			Help: "Total number of HTTP requests",
		},
		[]string{"service", "endpoint"},
	)

	requestDuration = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "http_request_duration_seconds",
			Help:    "Histogram for tracking request duration",
			Buckets: []float64{0.1, 0.11, 0.12, 0.13, 0.14, 0.15, 0.16, 0.17, 0.18, 0.19},
		},
		[]string{"service", "endpoint"},
	)
)

func init() {
	file, err := os.OpenFile("/var/log/backend.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0666)
	if err != nil {
		log.Fatalf("Failed to open log file: %v", err)
	}

	log.SetOutput(file)
	log.SetFlags(log.Ldate | log.Ltime | log.Lshortfile)
}

func setupTracing(ctx context.Context) func() {
	exporter, err := otlptracegrpc.New(ctx,
		otlptracegrpc.WithInsecure(),
		otlptracegrpc.WithEndpoint("tempo:4317"),
	)
	if err != nil {
		log.Fatalf("Ошибка создания OTLP экспортера: %v", err)
	}

	tp := trace.NewTracerProvider(
		trace.WithBatcher(exporter),
		trace.WithResource(resource.NewWithAttributes(
			semconv.SchemaURL,
			semconv.ServiceName("go-service"),
		)),
	)
	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.TraceContext{})

	return func() {
		if err := tp.Shutdown(ctx); err != nil {
			log.Printf("Ошибка остановки TracerProvider: %v", err)
		}
	}
}

func callOtherService(from, to string) {
	tracer := otel.Tracer("go-service")

	for {
		time.Sleep(time.Duration(rand.Intn(400)+100) * time.Millisecond)

		ctx, span := tracer.Start(context.Background(), "callOtherService")
		defer span.End()

		req, _ := http.NewRequestWithContext(ctx, "GET", "http://localhost:8080"+to, nil)
		client := http.Client{Transport: otelhttp.NewTransport(http.DefaultTransport)}
		resp, err := client.Do(req)

		if err != nil {
			log.Printf("[%s] Error calling %s: %v\n", from, to, err)
		} else {
			resp.Body.Close()
			log.Printf("[%s] Called %s\n", from, to)
		}
	}
}

func handler(service, endpoint string, duration int) http.HandlerFunc {
	tracer := otel.Tracer("go-service")

	return func(w http.ResponseWriter, r *http.Request) {
		_, span := tracer.Start(r.Context(), "handleRequest")
		defer span.End()

		start := time.Now()
		requestsTotal.WithLabelValues(service, endpoint).Inc()
		time.Sleep(time.Duration(rand.Intn(duration)+100) * time.Millisecond)
		duration := time.Since(start).Seconds()
		requestDuration.WithLabelValues(service, endpoint).Observe(duration)

		blob := make([]byte, rand.Intn(1000000))
		for i := range blob {
			blob[i] = byte(rand.Int31())
		}
		w.Write(blob)
	}
}

func main() {
	ctx := context.Background()
	shutdownTracing := setupTracing(ctx)
	defer shutdownTracing()

	prometheus.MustRegister(requestsTotal)
	prometheus.MustRegister(requestDuration)

	http.Handle("/service1", otelhttp.NewHandler(handler("service1", "/service1", 100), "/service1"))
	http.Handle("/service2", otelhttp.NewHandler(handler("service2", "/service2", 400), "/service2"))

	http.Handle("/metrics", promhttp.Handler())

	go callOtherService("service1", "/service2")
	go callOtherService("service2", "/service1")

	log.Println("Server running on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
