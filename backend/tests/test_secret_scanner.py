"""
Secret Scanner Unit Test Suite
Validates that the secret scanner detects OpenAI keys, AWS keys, private keys, and high entropy tokens.
Uses dynamic segment concatenation for fixture tokens to avoid triggering repository push protection.
"""
import pytest
from scripts.scan_secrets import PATTERNS, calculate_shannon_entropy

def test_shannon_entropy_calculation():
    low_entropy = "aaaaaaaaaaaaaaaa"
    high_entropy = "4f8a9b2c1d3e7f6a8b0c2d4e6f8a9b1c"
    
    assert calculate_shannon_entropy(low_entropy) < 1.0
    assert calculate_shannon_entropy(high_entropy) > 3.5


def test_patterns_detect_compromised_credentials():
    # 1. OpenAI Key Pattern
    token_openai = "sk-" + "proj-" + "abcde12345" + "T3BlbkFJ" + "abcde1234567890123456789"
    assert PATTERNS["OpenAI API Key"].search(token_openai) is not None

    # 2. RSA Private Key Header Pattern
    token_pem = "-----" + "BEGIN RSA PRIVATE KEY" + "-----\n" + "MIIEowIBAAKCAQEA..."
    assert PATTERNS["Generic Private Key"].search(token_pem) is not None

    # 3. GitHub Personal Token Pattern
    token_gh = "gh" + "p_" + "1234567890abcdefghijklmnopqrstuvwxyzAB"
    assert PATTERNS["GitHub Personal Token"].search(token_gh) is not None

    # 4. AWS Access Key ID Pattern
    token_aws = "AK" + "IAIOSFODNN7EXAMPLE"
    assert PATTERNS["AWS Access Key ID"].search(token_aws) is not None
