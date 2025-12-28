CXX=g++
CXXFLAGS=-std=c++17 -O2 -Wall -Wextra -I../lab3_text/cpp

TOKENIZER_SRC=../lab3_text/cpp/tokenizer.cpp
TOKENIZER_HDR=../lab3_text/cpp/tokenizer.h

all: builder bsearch

builder: builder.cpp stemmer.hpp $(TOKENIZER_SRC) $(TOKENIZER_HDR)
	$(CXX) $(CXXFLAGS) -o $@ builder.cpp $(TOKENIZER_SRC)

bsearch: search.cpp stemmer.hpp $(TOKENIZER_SRC) $(TOKENIZER_HDR)
	$(CXX) $(CXXFLAGS) -o $@ search.cpp $(TOKENIZER_SRC)

clean:
	rm -f builder bsearch

.PHONY: all clean
