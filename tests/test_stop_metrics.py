# 單元測試：驗證迴圈停止邏輯
import ast, pathlib, pytest

tools_path = pathlib.Path(__file__).resolve().parent.parent / 'root_agent' / 'agents' / 'moderator' / 'tools.py'
source = tools_path.read_text()
module_ast = ast.parse(source)
func_defs = [n for n in module_ast.body if isinstance(n, ast.FunctionDef) and n.name in {'update_metrics', 'should_stop'}]
module = ast.Module(body=func_defs, type_ignores=[])
namespace = {}
exec(compile(module, str(tools_path), 'exec'), namespace)
_update_metrics = namespace['update_metrics']
_should_stop = namespace['should_stop']


def test_metrics_stop_logic():
    """測試指標更新後無成長會觸發停止"""
    state = {"dispute_points": 1, "credibility": 0.5, "evidence": ["e1"]}
    _update_metrics(state)
    assert state["delta_dispute_points"] == 1
    assert state["delta_credibility"] == pytest.approx(0.5)
    assert state["new_evidence_gain"] == 1
    assert not _should_stop(state)

    _update_metrics(state)
    assert _should_stop(state)
