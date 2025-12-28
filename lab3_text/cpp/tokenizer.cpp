#include "tokenizer.h"

#include <algorithm>

namespace {
inline bool is_ascii_letter(unsigned char c) {
    return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z');
}

inline bool is_digit(unsigned char c) {
    return (c >= '0' && c <= '9');
}

inline bool is_cyrillic_start(unsigned char c1, unsigned char c2) {
    return ((c1 == 0xD0 && c2 >= 0x80 && c2 <= 0xBF) ||
            (c1 == 0xD1 && c2 >= 0x80 && c2 <= 0xBF));
}

inline bool is_token_char(const std::string& text, size_t pos, size_t& advance, bool keep_dashes, bool keep_apostrophes) {
    if (pos >= text.size()) {
        advance = 0;
        return false;
    }

    unsigned char c = static_cast<unsigned char>(text[pos]);

    if (is_ascii_letter(c) || is_digit(c)) {
        advance = 1;
        return true;
    }

    if (pos + 1 < text.size() && is_cyrillic_start(c, static_cast<unsigned char>(text[pos + 1]))) {
        advance = 2;
        return true;
    }

    if (keep_dashes && c == '-') {
        advance = 1;
        return true;
    }
    if (keep_apostrophes && c == '\'') {
        advance = 1;
        return true;
    }

    advance = 1;
    return false;
}

size_t utf8_char_count(const std::string& str) {
    size_t count = 0;
    for (size_t i = 0; i < str.size(); ) {
        unsigned char c = static_cast<unsigned char>(str[i]);
        if (c < 0x80) {
            i += 1;
        } else if ((c & 0xE0) == 0xC0) {
            i += 2;
        } else if ((c & 0xF0) == 0xE0) {
            i += 3;
        } else if ((c & 0xF8) == 0xF0) {
            i += 4;
        } else {
            i += 1;
        }
        ++count;
    }
    return count;
}
} // namespace

Tokenizer::Tokenizer()
    : lowercase_(true)
    , keep_dashes_(true)
    , keep_apostrophes_(true)
    , min_token_length_(1) {}

std::string Tokenizer::to_lower(const std::string& str) {
    std::string result;
    result.reserve(str.size());

    for (size_t i = 0; i < str.size();) {
        unsigned char c = static_cast<unsigned char>(str[i]);

        if (c >= 'A' && c <= 'Z') {
            result.push_back(static_cast<char>(c + 32));
            ++i;
        } else if (i + 1 < str.size() &&
                   static_cast<unsigned char>(str[i]) == 0xD0 &&
                   static_cast<unsigned char>(str[i + 1]) >= 0x90 &&
                   static_cast<unsigned char>(str[i + 1]) <= 0xAF) {
            result.push_back(static_cast<char>(0xD0));
            result.push_back(static_cast<char>(static_cast<unsigned char>(str[i + 1]) + 0x20));
            i += 2;
        } else if (i + 1 < str.size() &&
                   static_cast<unsigned char>(str[i]) == 0xD0 &&
                   static_cast<unsigned char>(str[i + 1]) == 0x81) {
            result.push_back(static_cast<char>(0xD1));
            result.push_back(static_cast<char>(0x91));
            i += 2;
        } else {
            result.push_back(str[i]);
            ++i;
        }
    }

    return result;
}

bool Tokenizer::is_valid_token(const std::string& token) {
    if (token.empty()) {
        return false;
    }

    size_t char_count = utf8_char_count(token);
    if (char_count < min_token_length_) {
        return false;
    }

    for (size_t i = 0; i < token.size(); ) {
        unsigned char c = static_cast<unsigned char>(token[i]);
        if (is_ascii_letter(c) || is_digit(c)) {
            return true;
        }
        if (i + 1 < token.size() && is_cyrillic_start(c, static_cast<unsigned char>(token[i + 1]))) {
            return true;
        }
        ++i;
    }
    return false;
}

std::vector<std::string> Tokenizer::tokenize(const std::string& text) {
    std::vector<std::string> tokens;
    size_t i = 0;
    while (i < text.size()) {
        size_t advance = 0;
        while (i < text.size() && !is_token_char(text, i, advance, keep_dashes_, keep_apostrophes_)) {
            ++i;
        }

        if (i < text.size()) {
            size_t token_start = i;
            while (i < text.size() && is_token_char(text, i, advance, keep_dashes_, keep_apostrophes_)) {
                i += advance;
            }

            std::string token = text.substr(token_start, i - token_start);
            while (!token.empty() && (token.front() == '-' || token.front() == '\'')) {
                token.erase(token.begin());
            }
            while (!token.empty() && (token.back() == '-' || token.back() == '\'')) {
                token.pop_back();
            }

            if (lowercase_) {
                token = to_lower(token);
            }

            if (is_valid_token(token)) {
                tokens.push_back(token);
            }
        }
    }

    return tokens;
}

std::vector<Tokenizer::Token> Tokenizer::tokenize_with_positions(const std::string& text) {
    std::vector<Token> tokens;
    size_t i = 0;
    while (i < text.size()) {
        size_t advance = 0;
        while (i < text.size() && !is_token_char(text, i, advance, keep_dashes_, keep_apostrophes_)) {
            ++i;
        }

        if (i < text.size()) {
            size_t token_start = i;
            while (i < text.size() && is_token_char(text, i, advance, keep_dashes_, keep_apostrophes_)) {
                i += advance;
            }

            std::string raw = text.substr(token_start, i - token_start);
            size_t trim_start = 0;
            while (trim_start < raw.size() && (raw[trim_start] == '-' || raw[trim_start] == '\'')) {
                ++trim_start;
            }
            size_t trim_end = 0;
            while (trim_end < raw.size() - trim_start &&
                   (raw[raw.size() - 1 - trim_end] == '-' || raw[raw.size() - 1 - trim_end] == '\'')) {
                ++trim_end;
            }

            std::string token_text = raw.substr(trim_start, raw.size() - trim_start - trim_end);
            if (lowercase_) {
                token_text = to_lower(token_text);
            }

            if (is_valid_token(token_text)) {
                Token t;
                t.text = token_text;
                t.position = token_start + trim_start;
                t.length = raw.size() - trim_start - trim_end;
                tokens.push_back(t);
            }
        }
    }
    return tokens;
}
