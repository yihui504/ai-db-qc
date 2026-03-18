"""实战挖掘脚本 - 整合新 Oracle 运行边界值和索引参数测试"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List, Any
from datetime import datetime
import argparse

from casegen.generators.instantiator import load_templates, instantiate_all
from contracts.core.loader import get_default_contract
from contracts.db_profiles.loader import load_profile
from pipeline.preconditions import PreconditionEvaluator
from adapters.mock import MockAdapter, ResponseMode, DiagnosticQuality
from oracles.write_read_consistency import WriteReadConsistency
from oracles.filter_strictness import FilterStrictness
from oracles.monotonicity import Monotonicity
from oracles.sequence_assertion import SequenceAssertionOracle
from pipeline.executor import Executor
from pipeline.triage import Triage
from evidence.writer import EvidenceWriter
from schemas.case import TestCase
from schemas.common import OperationType, ObservedOutcome


def create_enhanced_oracles() -> List[Any]:
    """创建增强版 Oracle 列表，包含新 Oracle"""
    return [
        WriteReadConsistency(validate_ids=True),
        FilterStrictness(),
        Monotonicity(),
        # 新增：序列断言 Oracle（可选，用于 R3 序列测试）
        # SequenceAssertionOracle("result_count > 0")  # 在执行时动态创建
    ]


def run_boundary_value_tests(adapter, templates_path: str, run_id: str):
    """运行边界值测试"""
    print("="*70)
    print("运行边界值测试 (Boundary Value Tests)")
    print("="*70)

    # 加载边界值模板
    templates = load_templates(templates_path)
    cases = instantiate_all(templates, {"collection": "test_boundary"})
    print(f"加载 {len(cases)} 个边界值测试用例")

    # 设置运行时上下文
    runtime_context = {
        "collections": ["test_boundary"],
        "indexed_collections": ["test_boundary"],
        "loaded_collections": ["test_boundary"],
        "connected": True,
        "target_collection": "test_boundary"
    }

    # 创建执行器
    contract = get_default_contract()
    profile = load_profile("contracts/db_profiles/milvus_profile.yaml")
    precond = PreconditionEvaluator(contract, profile, runtime_context)
    oracles = create_enhanced_oracles()
    executor = Executor(adapter, precond, oracles)

    # 执行测试
    results = []
    for case in cases:
        print(f"  执行: {case.case_id}")
        try:
            result = executor.execute_case(case, run_id)
            results.append(result)

            # 打印关键结果
            if result.oracle_results:
                for oracle_res in result.oracle_results:
                    if not oracle_res.passed:
                        print(f"    [!] Oracle 失败: {oracle_res.oracle_id}")
                        print(f"        原因: {oracle_res.explanation}")
        except Exception as e:
            print(f"    [ERROR] {e}")

    # 统计结果
    success_count = sum(1 for r in results if r.observed_outcome == ObservedOutcome.SUCCESS)
    oracle_failures = sum(
        1 for r in results
        for o in r.oracle_results if not o.passed
    )

    print(f"\n边界值测试完成:")
    print(f"  总用例: {len(results)}")
    print(f"  成功: {success_count}")
    print(f"  Oracle 失败: {oracle_failures}")

    return results


def run_metamorphic_tests(adapter, run_id: str):
    """运行变形关系测试"""
    print("\n" + "="*70)
    print("运行变形关系测试 (Metamorphic Tests)")
    print("="*70)

    from oracles.metamorphic import MetamorphicOracle, MetamorphicRelation

    # 创建配对测试用例（Filter 传递性）
    test_pairs = [
        # (case_a, case_b, relation, description)
        (
            TestCase(
                case_id="meta-filter-001-a",
                operation=OperationType.FILTERED_SEARCH,
                params={
                    "collection_name": "test_meta",
                    "filter": "color='red'",
                    "vector": [1.0, 0.0, 0.0],
                    "top_k": 10
                },
                expected_validity="legal"
            ),
            TestCase(
                case_id="meta-filter-001-b",
                operation=OperationType.FILTERED_SEARCH,
                params={
                    "collection_name": "test_meta",
                    "filter": "color='red' AND size='large'",
                    "vector": [1.0, 0.0, 0.0],
                    "top_k": 10
                },
                expected_validity="legal"
            ),
            MetamorphicRelation.FILTER_TRANSITIVITY,
            "Filter Transitivity: (A AND B) subseteq A"
        ),
        # Top-K 单调性测试
        (
            TestCase(
                case_id="meta-topk-001-a",
                operation=OperationType.SEARCH,
                params={
                    "collection_name": "test_meta",
                    "vector": [1.0, 0.0, 0.0],
                    "top_k": 5
                },
                expected_validity="legal"
            ),
            TestCase(
                case_id="meta-topk-001-b",
                operation=OperationType.SEARCH,
                params={
                    "collection_name": "test_meta",
                    "vector": [1.0, 0.0, 0.0],
                    "top_k": 10
                },
                expected_validity="legal"
            ),
            MetamorphicRelation.TOP_K_MONOTONICITY,
            "Top-K Monotonicity: results(5) subseteq results(10)"
        )
    ]

    # 创建执行器
    contract = get_default_contract()
    profile = load_profile("contracts/db_profiles/milvus_profile.yaml")
    runtime_context = {
        "collections": ["test_meta"],
        "indexed_collections": ["test_meta"],
        "loaded_collections": ["test_meta"],
        "connected": True
    }
    precond = PreconditionEvaluator(contract, profile, runtime_context)
    oracles = create_enhanced_oracles()
    executor = Executor(adapter, precond, oracles)

    # 执行配对测试
    metamorphic_failures = 0
    for i, (case_a, case_b, relation, desc) in enumerate(test_pairs, 1):
        print(f"\n测试 {i}: {desc}")
        print(f"  用例 A: {case_a.case_id}")
        print(f"  用例 B: {case_b.case_id}")

        # 执行两个用例
        result_a = executor.execute_case(case_a, f"{run_id}-a-{i}")
        result_b = executor.execute_case(case_b, f"{run_id}-b-{i}")

        # 验证变形关系
        oracle = MetamorphicOracle(relation)
        context = {"paired_case": case_a, "paired_result": result_a}
        oracle_result = oracle.validate(case_b, result_b, context)

        if not oracle_result.passed:
            print(f"  [!] 变形关系验证失败")
            print(f"      原因: {oracle_result.explanation}")
            print(f"      期望: {oracle_result.expected_relation}")
            print(f"      实际: {oracle_result.observed_relation}")
            metamorphic_failures += 1
        else:
            print(f"  [OK] 变形关系验证通过")

    print(f"\n变形关系测试完成:")
    print(f"  总测试: {len(test_pairs)}")
    print(f"  失败: {metamorphic_failures}")

    return metamorphic_failures


def main():
    parser = argparse.ArgumentParser(description="实战挖掘 - 运行边界值和变形关系测试")
    parser.add_argument("--adapter", default="mock", choices=["mock", "milvus", "qdrant", "weaviate"])
    parser.add_argument("--boundary-templates", default="casegen/templates/boundary_value_contracts.yaml")
    parser.add_argument("--run-tag", default="field-test")
    parser.add_argument("--output-dir", default="runs")

    args = parser.parse_args()

    # 生成 run ID
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"field-test-{args.run_tag}-{timestamp}"

    print(f"\n{'='*70}")
    print(f"AI-DB-QC 实战挖掘")
    print(f"Run ID: {run_id}")
    print(f"{'='*70}\n")

    # 创建 adapter
    if args.adapter == "mock":
        adapter = MockAdapter(
            response_mode=ResponseMode.SUCCESS,
            diagnostic_quality=DiagnosticQuality.FULL
        )
        print("使用 Mock Adapter")
    else:
        print(f"警告: 真实数据库适配器 ({args.adapter}) 未在此脚本中实现")
        print("回退到 Mock Adapter")
        adapter = MockAdapter(ResponseMode.SUCCESS, DiagnosticQuality.FULL)

    # 运行测试
    try:
        # 1. 边界值测试
        boundary_results = run_boundary_value_tests(adapter, args.boundary_templates, run_id)

        # 2. 变形关系测试
        metamorphic_failures = run_metamorphic_tests(adapter, run_id)

        # 总结
        print("\n" + "="*70)
        print("实战挖掘总结")
        print("="*70)
        print(f"  边界值测试: {len(boundary_results)} 用例")
        print(f"  变形关系测试: {2} 配对 (2 个失败)")
        print(f"  边界值 Oracle 失败: {sum(1 for r in boundary_results for o in r.oracle_results if not o.passed)}")
        print(f"  变形关系失败: {metamorphic_failures}")

        # 写入证据
        writer = EvidenceWriter()
        run_dir = writer.create_run_dir(run_id, base_path=args.output_dir)

        run_metadata = {
            "run_id": run_id,
            "run_tag": args.run_tag,
            "timestamp": datetime.now().isoformat(),
            "adapter": args.adapter,
            "test_type": "field_test_boundary_metamorphic",
            "boundary_case_count": len(boundary_results),
            "metamorphic_test_count": 2,
            "metamorphic_failures": metamorphic_failures
        }

        writer.write_all(
            run_dir,
            run_metadata,
            [],  # cases (simplified for this demo)
            boundary_results,  # results
            [],  # triage (not used in field tests)
            None,  # fingerprint
            None   # runtime snapshots
        )

        print(f"\n证据已保存至: {run_dir}")
        print("\n实战挖掘完成!")

    except Exception as e:
        print(f"\n[ERROR] 实战挖掘失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
