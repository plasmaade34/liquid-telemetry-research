// Minimal JSON parser, test-only. Not a general-purpose library -- just
// enough to read tests/test_vectors.json's flat, known shape, so the C++
// test runner has no external dependency to fetch or vendor. Do not reuse
// this outside the tests/ directory.

#pragma once

#include <cctype>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace jsonmini {

struct Value;
using Array = std::vector<Value>;
using Object = std::vector<std::pair<std::string, Value>>;

enum class Type { Null, Bool, Number, String, Array, Object };

struct Value {
    Type type = Type::Null;
    bool boolVal = false;
    double numVal = 0.0;
    std::string strVal;
    std::shared_ptr<Array> arrVal;
    std::shared_ptr<Object> objVal;

    bool isNull() const { return type == Type::Null; }
    bool isNumber() const { return type == Type::Number; }
    bool isString() const { return type == Type::String; }
    bool isArray() const { return type == Type::Array; }
    bool isObject() const { return type == Type::Object; }

    double asNumber() const { return numVal; }
    const std::string& asString() const { return strVal; }
    const Array& asArray() const { return *arrVal; }

    const Value* find(const std::string& key) const {
        if (type != Type::Object) return nullptr;
        for (auto& kv : *objVal) {
            if (kv.first == key) return &kv.second;
        }
        return nullptr;
    }
};

class Parser {
public:
    explicit Parser(const std::string& text) : s(text), pos(0) {}

    Value parse() {
        skipWs();
        return parseValue();
    }

private:
    const std::string& s;
    size_t pos;

    void skipWs() {
        while (pos < s.size() && std::isspace(static_cast<unsigned char>(s[pos]))) pos++;
    }
    char peek() const { return s[pos]; }
    char get() { return s[pos++]; }

    Value parseValue() {
        skipWs();
        char c = peek();
        if (c == '{') return parseObject();
        if (c == '[') return parseArray();
        if (c == '"') return parseString();
        if (c == 't' || c == 'f') return parseBool();
        if (c == 'n') return parseNull();
        return parseNumber();
    }

    Value parseObject() {
        Value v;
        v.type = Type::Object;
        v.objVal = std::make_shared<Object>();
        get();  // '{'
        skipWs();
        if (peek() == '}') {
            get();
            return v;
        }
        while (true) {
            skipWs();
            Value key = parseString();
            skipWs();
            if (get() != ':') throw std::runtime_error("json_mini: expected ':'");
            Value val = parseValue();
            v.objVal->emplace_back(key.strVal, val);
            skipWs();
            char c = get();
            if (c == ',') continue;
            if (c == '}') break;
            throw std::runtime_error("json_mini: expected ',' or '}'");
        }
        return v;
    }

    Value parseArray() {
        Value v;
        v.type = Type::Array;
        v.arrVal = std::make_shared<Array>();
        get();  // '['
        skipWs();
        if (peek() == ']') {
            get();
            return v;
        }
        while (true) {
            Value val = parseValue();
            v.arrVal->push_back(val);
            skipWs();
            char c = get();
            if (c == ',') continue;
            if (c == ']') break;
            throw std::runtime_error("json_mini: expected ',' or ']'");
        }
        return v;
    }

    Value parseString() {
        Value v;
        v.type = Type::String;
        get();  // opening quote
        std::string out;
        while (peek() != '"') {
            char c = get();
            if (c == '\\') {
                char e = get();
                switch (e) {
                    case 'n': out += '\n'; break;
                    case 't': out += '\t'; break;
                    case 'r': out += '\r'; break;
                    case '"': out += '"'; break;
                    case '\\': out += '\\'; break;
                    case '/': out += '/'; break;
                    default: out += e; break;
                }
            } else {
                out += c;
            }
        }
        get();  // closing quote
        v.strVal = out;
        return v;
    }

    Value parseBool() {
        Value v;
        v.type = Type::Bool;
        if (s.compare(pos, 4, "true") == 0) {
            v.boolVal = true;
            pos += 4;
        } else {
            v.boolVal = false;
            pos += 5;
        }
        return v;
    }

    Value parseNull() {
        Value v;
        v.type = Type::Null;
        pos += 4;
        return v;
    }

    Value parseNumber() {
        Value v;
        v.type = Type::Number;
        size_t start = pos;
        if (peek() == '-') get();
        while (pos < s.size()) {
            char c = peek();
            if (std::isdigit(static_cast<unsigned char>(c)) || c == '.' || c == 'e' || c == 'E' || c == '+' ||
                c == '-') {
                get();
            } else {
                break;
            }
        }
        v.numVal = std::stod(s.substr(start, pos - start));
        return v;
    }
};

inline Value parse(const std::string& text) {
    Parser p(text);
    return p.parse();
}

}  // namespace jsonmini
