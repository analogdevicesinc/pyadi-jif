set -xe
# export PATH=$PATH:/usr/local/go/bin

## To update
# rm go.sum
# go mod download oss.terrastruct.com/d2@latest
# go mod tidy

go install oss.terrastruct.com/d2@latest
go run d2lib.go
go build -buildmode=c-shared -o d2lib.so d2lib.go