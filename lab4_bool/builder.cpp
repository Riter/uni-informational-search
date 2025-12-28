#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "../lab3_text/cpp/tokenizer.h"
#include "stemmer.hpp"

struct DocEntry { std::string id; };

struct Index {
    std::vector<DocEntry> docs;
    std::unordered_map<std::string, std::vector<uint32_t>> postings;
};

static void add_postings(Index& idx, uint32_t doc_id, const std::vector<std::string>& tokens, bool use_stem) {
    std::unordered_set<std::string> seen;
    for (const auto& tok : tokens) {
        std::string term = use_stem ? stem_token(tok) : tok;
        if (term.empty()) continue;
        if (seen.insert(term).second) {
            auto& vec = idx.postings[term];
            vec.push_back(doc_id);
        }
    }
}

// --- JSONL parsing (very small subset) ---
static bool decode_json_string(const std::string& src, size_t& pos, std::string& out) {
    if (pos >= src.size() || src[pos] != '"') return false;
    ++pos;
    out.clear();
    while (pos < src.size()) {
        char c = src[pos++];
        if (c == '\\') {
            if (pos >= src.size()) return false;
            char esc = src[pos++];
            switch (esc) {
                case '"': out.push_back('"'); break;
                case '\\': out.push_back('\\'); break;
                case 'n': out.push_back('\n'); break;
                case 't': out.push_back('\t'); break;
                case 'r': out.push_back('\r'); break;
                default: out.push_back(esc); break;
            }
        } else if (c == '"') {
            return true;
        } else {
            out.push_back(c);
        }
    }
    return false;
}

static bool extract_field(const std::string& line, const std::string& key, std::string& value) {
    std::string pattern = "\"" + key + "\"";
    auto p = line.find(pattern);
    if (p == std::string::npos) return false;
    p = line.find(':', p + pattern.size());
    if (p == std::string::npos) return false;
    while (p < line.size() && std::isspace(static_cast<unsigned char>(line[p]))) ++p;
    if (p >= line.size()) return false;
    // move to first quote
    while (p < line.size() && line[p] != '"') ++p;
    if (p >= line.size()) return false;
    return decode_json_string(line, p, value);
}

static void write_uint32(std::ofstream& out, uint32_t v) {
    out.write(reinterpret_cast<const char*>(&v), sizeof(v));
}

static void write_string(std::ofstream& out, const std::string& s) {
    uint32_t len = static_cast<uint32_t>(s.size());
    write_uint32(out, len);
    out.write(s.data(), len);
}

static void save_index(const Index& idx, const std::string& path) {
    std::ofstream out(path, std::ios::binary);
    if (!out) throw std::runtime_error("Cannot open index file for write");

    out.write("BIDX1", 5);
    write_uint32(out, static_cast<uint32_t>(idx.docs.size()));
    write_uint32(out, static_cast<uint32_t>(idx.postings.size()));

    // docs
    for (const auto& d : idx.docs) {
        write_string(out, d.id);
    }

    // postings
    for (const auto& kv : idx.postings) {
        write_string(out, kv.first);
        const auto& plist = kv.second;
        write_uint32(out, static_cast<uint32_t>(plist.size()));
        out.write(reinterpret_cast<const char*>(plist.data()), plist.size() * sizeof(uint32_t));
    }
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::cerr << "Usage: builder <corpus.jsonl> <out_index.bin> [--nostem]\n";
        return 1;
    }
    std::string corpus_path = argv[1];
    std::string out_path = argv[2];
    bool use_stem = true;
    if (argc > 3 && std::string(argv[3]) == "--nostem") use_stem = false;

    std::ifstream in(corpus_path);
    if (!in) {
        std::cerr << "Cannot open corpus file\n";
        return 1;
    }

    Tokenizer tok;
    tok.set_lowercase(true);
    tok.set_min_token_length(2);

    Index idx;
    idx.docs.reserve(1024);

    std::string line;
    uint32_t doc_id = 0;
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        std::string id, text;
        if (!extract_field(line, "id", id)) continue;
        if (!extract_field(line, "text", text)) continue;

        idx.docs.push_back({id});
        auto tokens = tok.tokenize(text);
        add_postings(idx, doc_id, tokens, use_stem);
        ++doc_id;
    }

    for (auto& kv : idx.postings) {
        auto& v = kv.second;
        std::sort(v.begin(), v.end());
        v.erase(std::unique(v.begin(), v.end()), v.end());
    }

    save_index(idx, out_path);
    std::cout << "Indexed docs: " << idx.docs.size() << "\n";
    std::cout << "Terms: " << idx.postings.size() << "\n";
    std::cout << "Saved to " << out_path << "\n";
    return 0;
}
