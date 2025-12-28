#include "tokenizer.h"

#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <set>
#include <string>
#include <vector>

struct Statistics {
    size_t total_tokens = 0;
    size_t total_chars = 0;
    size_t unique_tokens = 0;
    double avg_token_length = 0.0;
    double time_seconds = 0.0;
    size_t input_size_bytes = 0;
};

std::string read_file(const std::string& filename) {
    std::ifstream file(filename, std::ios::binary);
    if (!file) {
        throw std::runtime_error("Cannot open input file: " + filename);
    }
    return std::string(
        (std::istreambuf_iterator<char>(file)),
        std::istreambuf_iterator<char>()
    );
}

void save_tokens(const std::string& filename, const std::vector<std::string>& tokens) {
    std::ofstream out(filename, std::ios::binary);
    if (!out) {
        throw std::runtime_error("Cannot write tokens file: " + filename);
    }
    for (const auto& token : tokens) {
        out << token << "\n";
    }
}

Statistics calculate_statistics(const std::vector<std::string>& tokens, double time_seconds, size_t input_size) {
    Statistics stats;
    stats.total_tokens = tokens.size();
    stats.time_seconds = time_seconds;
    stats.input_size_bytes = input_size;

    std::set<std::string> uniq(tokens.begin(), tokens.end());
    stats.unique_tokens = uniq.size();

    for (const auto& token : tokens) {
        stats.total_chars += token.size();
    }
    if (stats.total_tokens > 0) {
        stats.avg_token_length = static_cast<double>(stats.total_chars) / stats.total_tokens;
    }
    return stats;
}

void print_statistics(const Statistics& stats) {
    std::cout << "\n== Tokenization stats ==\n";
    std::cout << "Total tokens: " << stats.total_tokens << "\n";
    std::cout << "Unique tokens: " << stats.unique_tokens << "\n";
    std::cout << "Average length: " << std::fixed << std::setprecision(2) << stats.avg_token_length << " chars\n";
    std::cout << "\n== Performance ==\n";
    std::cout << "Input size: " << stats.input_size_bytes / 1024.0 << " KB\n";
    std::cout << "Elapsed: " << std::fixed << std::setprecision(3) << stats.time_seconds << " s\n";
    if (stats.time_seconds > 0) {
        double speed_kb = (stats.input_size_bytes / 1024.0) / stats.time_seconds;
        double speed_tokens = stats.total_tokens / stats.time_seconds;
        std::cout << "Throughput: " << std::fixed << std::setprecision(2) << speed_kb << " KB/s\n";
        std::cout << "Throughput: " << std::fixed << std::setprecision(0) << speed_tokens << " tokens/s\n";
    }
    std::cout << std::endl;
}

void print_help() {
    std::cout << "Usage: tokenizer [options] <input_file> [output_file]\n"
              << "Options:\n"
              << "  -h, --help            Show help\n"
              << "  -s, --stats           Print statistics\n"
              << "  -m, --min-length N    Minimum token length (default 1)\n"
              << "  --no-lowercase        Do not lowercase tokens\n"
              << "  --keep-dash           Keep inner dashes (default on)\n"
              << "  --keep-apostrophe     Keep inner apostrophes (default on)\n";
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        print_help();
        return 1;
    }

    std::string input_file;
    std::string output_file = "tokens.txt";
    bool show_stats = false;
    bool lowercase = true;
    bool keep_dash = true;
    bool keep_apostrophe = true;
    size_t min_length = 1;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "-h" || arg == "--help") {
            print_help();
            return 0;
        } else if (arg == "-s" || arg == "--stats") {
            show_stats = true;
        } else if (arg == "-m" || arg == "--min-length") {
            if (i + 1 < argc) {
                min_length = static_cast<size_t>(std::stoul(argv[++i]));
            }
        } else if (arg == "--no-lowercase") {
            lowercase = false;
        } else if (arg == "--keep-dash") {
            keep_dash = true;
        } else if (arg == "--keep-apostrophe") {
            keep_apostrophe = true;
        } else if (input_file.empty()) {
            input_file = arg;
        } else if (output_file == "tokens.txt") {
            output_file = arg;
        }
    }

    if (input_file.empty()) {
        std::cerr << "Input file is required.\n";
        return 1;
    }

    try {
        std::string text = read_file(input_file);

        Tokenizer tokenizer;
        tokenizer.set_lowercase(lowercase);
        tokenizer.set_min_token_length(min_length);
        tokenizer.set_keep_dashes(keep_dash);
        tokenizer.set_keep_apostrophes(keep_apostrophe);

        auto start = std::chrono::high_resolution_clock::now();
        std::vector<std::string> tokens = tokenizer.tokenize(text);
        auto end = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> duration = end - start;

        save_tokens(output_file, tokens);

        if (show_stats) {
            Statistics stats = calculate_statistics(tokens, duration.count(), text.size());
            print_statistics(stats);
        } else {
            std::cout << "Tokens: " << tokens.size() << "\n";
            std::cout << "Elapsed: " << std::fixed << std::setprecision(3) << duration.count() << " s\n";
        }
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << std::endl;
        return 1;
    }

    return 0;
}
