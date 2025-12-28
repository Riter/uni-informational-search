#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stack>
#include <string>
#include <unordered_map>
#include <vector>

#include "../lab3_text/cpp/tokenizer.h"
#include "stemmer.hpp"

struct Index {
    std::vector<std::string> docs;
    std::unordered_map<std::string, std::vector<uint32_t>> postings;
};

static uint32_t read_uint32(std::ifstream& in) {
    uint32_t v;
    in.read(reinterpret_cast<char*>(&v), sizeof(v));
    return v;
}

static std::string read_string(std::ifstream& in) {
    uint32_t len = read_uint32(in);
    std::string s(len, '\0');
    in.read(s.data(), len);
    return s;
}

static Index load_index(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) throw std::runtime_error("cannot open index file");
    char magic[5];
    in.read(magic, 5);
    if (std::string(magic, 5) != "BIDX1") {
        throw std::runtime_error("bad index file");
    }
    Index idx;
    auto doc_count = read_uint32(in);
    auto term_count = read_uint32(in);
    idx.docs.reserve(doc_count);
    for (uint32_t i = 0; i < doc_count; ++i) {
        idx.docs.push_back(read_string(in));
    }
    for (uint32_t t = 0; t < term_count; ++t) {
        std::string term = read_string(in);
        uint32_t len = read_uint32(in);
        std::vector<uint32_t> plist(len);
        in.read(reinterpret_cast<char*>(plist.data()), len * sizeof(uint32_t));
        idx.postings.emplace(std::move(term), std::move(plist));
    }
    return idx;
}

static std::vector<uint32_t> set_and(const std::vector<uint32_t>& a, const std::vector<uint32_t>& b) {
    std::vector<uint32_t> out;
    out.reserve(std::min(a.size(), b.size()));
    size_t i = 0, j = 0;
    while (i < a.size() && j < b.size()) {
        if (a[i] == b[j]) { out.push_back(a[i]); ++i; ++j; }
        else if (a[i] < b[j]) ++i;
        else ++j;
    }
    return out;
}

static std::vector<uint32_t> set_or(const std::vector<uint32_t>& a, const std::vector<uint32_t>& b) {
    std::vector<uint32_t> out;
    out.reserve(a.size() + b.size());
    size_t i = 0, j = 0;
    while (i < a.size() || j < b.size()) {
        uint32_t v;
        if (j >= b.size() || (i < a.size() && a[i] <= b[j])) { v = a[i++]; }
        else { v = b[j++]; }
        if (out.empty() || out.back() != v) out.push_back(v);
    }
    return out;
}

static std::vector<uint32_t> set_not(const std::vector<uint32_t>& universe, const std::vector<uint32_t>& b) {
    std::vector<uint32_t> out;
    out.reserve(universe.size());
    size_t i = 0, j = 0;
    while (i < universe.size()) {
        if (j >= b.size()) {
            out.insert(out.end(), universe.begin() + i, universe.end());
            break;
        }
        if (universe[i] == b[j]) { ++i; ++j; }
        else if (universe[i] < b[j]) { out.push_back(universe[i]); ++i; }
        else { ++j; }
    }
    return out;
}

enum class Op { TERM, AND, OR, NOT };
struct Token {
    Op type;
    std::string term;
};

static std::vector<Token> parse_query(const std::string& raw, Tokenizer& tokenizer, bool use_stem) {
    std::vector<Token> tokens;
    auto words = tokenizer.tokenize(raw);
    for (auto& w : words) {
        if (w == "and") tokens.push_back({Op::AND, {}});
        else if (w == "or") tokens.push_back({Op::OR, {}});
        else if (w == "not") tokens.push_back({Op::NOT, {}});
        else {
            tokens.push_back({Op::TERM, use_stem ? stem_token(w) : w});
        }
    }
    return tokens;
}

static int precedence(Op op) {
    if (op == Op::NOT) return 2;
    if (op == Op::AND) return 1;
    return 0;
}

static std::vector<Token> to_postfix(const std::vector<Token>& infix) {
    std::vector<Token> output;
    std::stack<Op> ops;
    for (const auto& t : infix) {
        if (t.type == Op::TERM) {
            output.push_back(t);
        } else {
            while (!ops.empty() && precedence(ops.top()) >= precedence(t.type)) {
                output.push_back({ops.top(), {}});
                ops.pop();
            }
            ops.push(t.type);
        }
    }
    while (!ops.empty()) {
        output.push_back({ops.top(), {}});
        ops.pop();
    }
    return output;
}

static std::vector<uint32_t> postings_for(const Index& idx, const std::string& term) {
    auto it = idx.postings.find(term);
    if (it == idx.postings.end()) return {};
    return it->second;
}

static std::vector<uint32_t> evaluate(const Index& idx, const std::vector<Token>& postfix) {
    std::vector<uint32_t> universe(idx.docs.size());
    for (uint32_t i = 0; i < universe.size(); ++i) universe[i] = i;

    std::vector<std::vector<uint32_t>> stack;
    for (const auto& t : postfix) {
        if (t.type == Op::TERM) {
            stack.push_back(postings_for(idx, t.term));
        } else if (t.type == Op::NOT) {
            auto a = stack.back(); stack.pop_back();
            stack.push_back(set_not(universe, a));
        } else {
            auto b = stack.back(); stack.pop_back();
            auto a = stack.back(); stack.pop_back();
            if (t.type == Op::AND) stack.push_back(set_and(a, b));
            else stack.push_back(set_or(a, b));
        }
    }
    return stack.empty() ? std::vector<uint32_t>{} : stack.back();
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: bsearch <index.bin> [--nostem]\n";
        return 1;
    }
    std::string index_path = argv[1];
    bool use_stem = true;
    if (argc > 2 && std::string(argv[2]) == "--nostem") use_stem = false;

    Index idx = load_index(index_path);
    std::cerr << "Loaded index: " << idx.docs.size() << " docs, " << idx.postings.size() << " terms\n";

    Tokenizer tokenizer;
    tokenizer.set_lowercase(true);
    tokenizer.set_min_token_length(2);

    std::string query;
    std::cout << "Enter query (AND/OR/NOT, Ctrl+D to exit):\n";
    while (std::getline(std::cin, query)) {
        auto infix = parse_query(query, tokenizer, use_stem);
        auto postfix = to_postfix(infix);
        auto result = evaluate(idx, postfix);
        std::cout << "Found " << result.size() << " docs\n";
        for (auto doc_id : result) {
            if (doc_id < idx.docs.size())
                std::cout << idx.docs[doc_id] << "\n";
        }
        std::cout << "----\n";
    }
    return 0;
}
