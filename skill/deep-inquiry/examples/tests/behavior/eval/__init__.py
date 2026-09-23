"""eval 固化包：三类命题（机制型/概念型/争议型）的确定性回归夹具。

组成：
- base.py：CasePack 用例协议 + ScriptedHost（按 request.json 确定性产出 judgment）
- cases/：三类命题的内容与「理想宿主行为」脚本（含预埋缺口、反例、悬置处置）
- runner.py：单用例完整学习-教学闭环驱动器与断言画像

设计原则与生产协议一致：规则在内核、判断在宿主。这里的宿主是确定性脚本，
真实宿主模型验证时只需把 ScriptedHost 换成模型对 request.json 的判断，
runner 的断言画像不变——同一把尺子量脚本与模型。
"""
