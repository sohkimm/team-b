#!/usr/bin/env python
"""NC 검증 파이프라인 CLI 진입점.

사용법:
    python run_validation.py FILE_A FILE_B --var-a VAR --var-b VAR [--outdir DIR]
"""
import argparse
import sys
from src.pipeline import run


def main():
    parser = argparse.ArgumentParser(
        description="두 NetCDF 파일을 WGS84 표준화 후 통계 검증합니다."
    )
    parser.add_argument("file_a", help="첫 번째 NC 파일 경로")
    parser.add_argument("file_b", help="두 번째 NC 파일 경로")
    parser.add_argument("--var-a", required=True,
                        help="파일 A에서 비교할 변수명")
    parser.add_argument("--var-b", required=True,
                        help="파일 B에서 비교할 변수명")
    parser.add_argument("--outdir", default="results",
                        help="결과 저장 디렉토리 (기본값: results)")
    args = parser.parse_args()

    cfg = {
        "file_a": args.file_a,
        "file_b": args.file_b,
        "var_a": args.var_a,
        "var_b": args.var_b,
        "outdir": args.outdir,
    }

    try:
        result = run(cfg)
        print(f"\n완료. 결과 보고서: {result['report']}")
        return 0
    except (ValueError, KeyError, NotImplementedError) as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
