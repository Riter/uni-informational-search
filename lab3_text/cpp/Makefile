CXX=g++
CXXFLAGS=-std=c++17 -O2 -Wall -Wextra

SRC=tokenizer_main.cpp tokenizer.cpp
HDR=tokenizer.h
BIN=tokenizer

all: $(BIN)

$(BIN): $(SRC) $(HDR)
	$(CXX) $(CXXFLAGS) -o $(BIN) $(SRC)

clean:
	rm -f $(BIN)

.PHONY: all clean
