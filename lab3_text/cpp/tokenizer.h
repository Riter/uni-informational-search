#ifndef SIMPLE_TOKENIZER_H
#define SIMPLE_TOKENIZER_H

#include <string>
#include <vector>

class Tokenizer {
public:
    Tokenizer();

    struct Token {
        std::string text;
        size_t position;
        size_t length;
    };

    std::vector<std::string> tokenize(const std::string& text);
    std::vector<Token> tokenize_with_positions(const std::string& text);

    void set_lowercase(bool value) { lowercase_ = value; }
    void set_min_token_length(size_t value) { min_token_length_ = value; }
    void set_keep_dashes(bool value) { keep_dashes_ = value; }
    void set_keep_apostrophes(bool value) { keep_apostrophes_ = value; }

private:
    bool lowercase_;
    bool keep_dashes_;
    bool keep_apostrophes_;
    size_t min_token_length_;

    std::string to_lower(const std::string& str);
    bool is_valid_token(const std::string& token);
};

#endif // SIMPLE_TOKENIZER_H
