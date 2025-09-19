from pathlib import Path
import importlib.util
import sys

module_path = Path("Python/Prediction/sentiment_analyzer.py").resolve()
spec = importlib.util.spec_from_file_location("sentiment_analyzer", module_path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

SentimentAnalyzer = module.SentimentAnalyzer

analyzer = SentimentAnalyzer()
for sentence in [
    "매출이 증가하고 흑자로 전환했다",
    "적자 확대와 비용 증가로 우려가 커진다",
    "방향성 없이 혼조세가 이어진다",
]:
    print(sentence, '->', analyzer.analyze_sentiment(sentence))
