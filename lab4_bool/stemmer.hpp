#ifndef SIMPLE_STEMMER_HPP
#define SIMPLE_STEMMER_HPP

#include <string>
#include <vector>

inline bool has_cyrillic(const std::string& s) {
    for (unsigned char c : s) {
        if (c >= 0xD0) return true; // грубая эвристика для UTF-8 кириллицы
    }
    return false;
}

inline std::string strip_suffix(const std::string& word, const std::vector<std::string>& suffixes) {
    for (const auto& suf : suffixes) {
        if (word.size() > suf.size() + 1 && word.rfind(suf) == word.size() - suf.size()) {
            return word.substr(0, word.size() - suf.size());
        }
    }
    return word;
}

inline std::string stem_token(const std::string& token) {
    static const std::vector<std::string> ru = {
        "иями","ями","ами","ией","ой","ей","ии","ий","ый","ия","ья","я","ию","ью","ю",
        "ов","ев","ем","ам","ом","ах","ях","иям","ям","ею","ие","ые","ое","иею","ией"
    };
    static const std::vector<std::string> en = {
        "ingly","edly","ness","ment","ious","tion","sion","able","ible","ally","less",
        "ful","est","ers","ies","ing","ed","ly","es","s"
    };

    if (token.size() <= 2) return token;

    if (has_cyrillic(token)) {
        return strip_suffix(token, ru);
    }
    return strip_suffix(token, en);
}

#endif // SIMPLE_STEMMER_HPP
