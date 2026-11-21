"""Original practice exercises and their judge fixtures."""

from dataclasses import dataclass
from pathlib import Path
import re
from textwrap import dedent


@dataclass(frozen=True)
class Case:
    name: str
    arguments: str
    expected: str | None = None


def exercise(id, title, level, runtime, topic, summary, rules, example, starter, hint, explanation, solution, cases):
    return dict(id=id, title=title, level=level, runtime=runtime, topic=topic, summary=summary,
                rules=rules, example=example, starter=dedent(starter).lstrip(),
                hint=hint, explanation=explanation, solution=dedent(solution).lstrip(),
                cases=[Case(*case) for case in cases])


PROBLEMS = [
    exercise(
        "softmax", "Stable Softmax", "入门", "NumPy", "张量基础",
        "沿指定维度计算 softmax。输入的 logits 可以很大，也可以全部是负数。输出应与输入形状相同。",
        ["输入 x 为浮点 NumPy ndarray，axis 是有效的维度索引，支持负数。",
         "沿 axis 保留归一化维度，结果在该维度上的和为 1。",
         "用基础 NumPy 运算实现。输入包含有限值。"],
        "x = np.array([[1000., 1001.], [-1000., -1000.]])\n"
        "axis = -1\n"
        "→ [[0.268941, 0.731059], [0.5, 0.5]]",
        '''
        import numpy as np


        def stable_softmax(x, axis=-1):
            # x: NumPy array
            pass
        ''',
        "先沿目标轴减去该轴上的最大值。用 keepdims=True 保留广播需要的维度。",
        "减去同一行的常数不会改变 softmax。减去最大值后，指数的输入至多为 0。",
        '''
        import numpy as np


        def stable_softmax(x, axis=-1):
            shifted = x - np.max(x, axis=axis, keepdims=True)
            weights = np.exp(shifted)
            return weights / np.sum(weights, axis=axis, keepdims=True)
        ''',
        [("大 logits", "(np.array([[1000., 1001.], [-1000., -1000.]]), -1)"),
         ("向量输入", "(np.array([1., 2., 3.]), 0)"),
         ("按列归一化", "(np.array([[3., 0.], [4., -1000.]]), 0)"),
         ("三维张量与负轴", "(np.arange(24, dtype=float).reshape(2, 3, 4), -2)"),
         ("单元素轴", "(np.array([[-2000.], [2000.]]), -1)")],
    ),
    exercise(
        "cross-entropy", "Stable Cross-Entropy", "进阶", "PyTorch", "损失函数",
        "从一批未归一化的 logits 计算平均多类交叉熵。即使正确类别的 logit 远小于其他类别，结果也应保持有限。",
        ["logits 为 [B, C] 浮点张量，targets 为 [B] 的 torch.long 类别索引。",
         "返回标量张量，保留对 logits 的梯度。",
         "用基础张量操作实现，可以用 torch.logsumexp。"],
        "logits = torch.tensor([[2., 1., 0.]])\n"
        "targets = torch.tensor([0])\n"
        "→ tensor(0.407606)",
        '''
        import torch


        def cross_entropy(logits, targets):
            # logits: [B, C], targets: [B]
            pass
        ''',
        "每个样本的损失等于这一行的 logsumexp 减掉正确类别的 logit。",
        "交叉熵等于正确类别负的 log 概率。用 gather 一次取出每行的目标 logit。",
        '''
        import torch


        def cross_entropy(logits, targets):
            correct = logits.gather(1, targets[:, None]).squeeze(1)
            return (torch.logsumexp(logits, dim=1) - correct).mean()
        ''',
        [("单个样本", "(torch.tensor([[2., 1., 0.]], dtype=torch.float64), torch.tensor([0]))"),
         ("批量输入", "(torch.tensor([[1., 0.], [-1., 2.]]), torch.tensor([0, 1]))"),
         ("极端且预测错误", "(torch.tensor([[-1000., 1000.], [900., -900.]]), torch.tensor([0, 1]))"),
         ("只有一个类别", "(torch.tensor([[100.], [-10.]]), torch.zeros(2, dtype=torch.long))"),
         ("梯度检查", "(torch.linspace(-1., 2., 12).reshape(3, 4).requires_grad_(), torch.tensor([1, 0, 3]))")],
    ),
    exercise(
        "masked-attention", "Masked Multi-Head Attention", "进阶", "PyTorch", "Attention",
        "实现带布尔 mask 的 scaled dot-product attention。输入已经按 head 拆开，query 和 key 可以有不同的长度。",
        ["q 为 [B, H, Tq, D]，k 为 [B, H, Tk, D]，v 为 [B, H, Tk, Dv]。",
         "mask 为 None 或可广播至 [B, H, Tq, Tk] 的布尔张量，True 表示可见。",
         "沿 key 维做 softmax。一个 query 完全不可见时，该 query 的输出为全零。",
         "返回 [B, H, Tq, Dv]。用基础张量运算实现。"],
        "q = k = torch.zeros(1, 1, 2, 1)\n"
        "v = torch.tensor([[[[2.], [6.]]]])\n"
        "mask = torch.tensor([[True, False], [True, True]])\n"
        "→ tensor([[[[2.], [4.]]]])",
        '''
        import torch
        import math


        def masked_attention(q, k, v, mask=None):
            # q: [B, H, Tq, D], k: [B, H, Tk, D]
            # v: [B, H, Tk, Dv]
            pass
        ''',
        "计算 q @ k.transpose(-2, -1)，沿最后一维归一化。先识别全被遮挡的行，避免 softmax([-inf, ...]) 产生 NaN。",
        "部分可见的行用 -inf 屏蔽。全遮挡的行先给 softmax 一个有限输入，再把对应权重清零。",
        '''
        import math
        import torch


        def masked_attention(q, k, v, mask=None):
            scores = (q @ k.transpose(-2, -1)) / math.sqrt(q.shape[-1])
            if mask is None:
                return scores.softmax(dim=-1) @ v
            visible = mask.any(dim=-1, keepdim=True)
            scores = scores.masked_fill(~mask, -torch.inf)
            scores = torch.where(visible, scores, 0.)
            weights = torch.where(visible, scores.softmax(dim=-1), 0.)
            return weights @ v
        ''',
        [("两步 causal mask", "(torch.zeros(1, 1, 2, 1), torch.zeros(1, 1, 2, 1), torch.tensor([[[[2.], [6.]]]]), torch.tensor([[True, False], [True, True]]))"),
         ("Cross-attention", "(seq(1, 2, 2, 3), seq(1, 2, 4, 3), seq(1, 2, 4, 5), None)"),
         ("全遮挡的一行", "(seq(1, 2, 2, 3), seq(1, 2, 3, 3), seq(1, 2, 3, 2), torch.tensor([[False, False, False], [True, False, True]]))"),
         ("跨 batch 和 head 广播", "(seq(2, 3, 2, 7), seq(2, 3, 4, 7), seq(2, 3, 4, 5), (torch.arange(16).reshape(2, 1, 2, 4) % 3 == 1))"),
         ("四维 mask 与单个 key", "(seq(2, 2, 3, 2), seq(2, 2, 1, 2), seq(2, 2, 1, 4), (torch.arange(12).reshape(2, 2, 3, 1) % 2 == 0))")],
    ),
    exercise(
        "kv-cache", "KV-Cache Decode Step", "进阶", "PyTorch", "Attention",
        "实现增量解码的一步。把当前 token 的 key 和 value 加到缓存，再用新的 query 对目前可见的全部位置做 attention。",
        ["q、k_new、v_new 为 [B, H, 1, D]。缓存 k_cache、v_cache 为 [B, H, T, D]，T 可以为 0。",
         "按 token 维拼接缓存。当前 query 可以看到缓存及当前 token。",
         "返回 (out, keys, values)，其中 out 为 [B, H, 1, D]，缓存长度为 T+1。",
         "保持输入缓存可复用，使用基础张量运算。"],
        "q = k_new = torch.zeros(1, 1, 1, 1)\n"
        "缓存的 value = 2，当前 value = 6\n"
        "→ out = 4，新的 values = [2, 6]",
        '''
        import torch
        import math


        def decode_step(q, k_new, v_new, k_cache, v_cache):
            # Return (out, updated keys, updated values).
            pass
        ''',
        "在倒数第二个维度拼接 K、V。新 query 只有一行，乘上拼接后 K 的转置。",
        "这一步只计算新 query 对现有 K 的权重。缓存的序列长度增加 1。",
        '''
        import torch
        import math


        def decode_step(q, k_new, v_new, k_cache, v_cache):
            keys = torch.cat((k_cache, k_new), dim=-2)
            values = torch.cat((v_cache, v_new), dim=-2)
            logits = (q @ keys.transpose(-2, -1)) / math.sqrt(q.shape[-1])
            return logits.softmax(dim=-1) @ values, keys, values
        ''',
        [("追加到已有缓存", "(torch.zeros(1, 1, 1, 1), torch.zeros(1, 1, 1, 1), torch.tensor([[[[6.]]]]), torch.zeros(1, 1, 1, 1), torch.tensor([[[[2.]]]]))"),
         ("冷启动空缓存", "(seq(1, 2, 1, 2), seq(1, 2, 1, 2), seq(1, 2, 1, 2), torch.empty(1, 2, 0, 2), torch.empty(1, 2, 0, 2))"),
         ("多 batch、多 head", "(seq(2, 3, 1, 4), -seq(2, 3, 1, 4), seq(2, 3, 1, 4) + 1., seq(2, 3, 5, 4), -seq(2, 3, 5, 4))"),
         ("大分数的数值稳定性", "(torch.full((1, 1, 1, 2), 1000.), torch.full((1, 1, 1, 2), 1000.), seq(1, 1, 1, 2), seq(1, 1, 7, 2), seq(1, 1, 7, 2))")],
    ),
    exercise(
        "clip-loss", "Symmetric CLIP Loss", "进阶", "PyTorch", "多模态",
        "给定成对排列的图像和文本向量，用 batch 内的其他样本做负例，计算双向对比损失。",
        ["images、texts 均为 [B, D] 浮点张量，第 i 行是一对正样本。",
         "逐行 L2 归一化，范数最低取 1e-12。相似度除以正数 temperature。",
         "返回 image-to-text 与 text-to-image 的平均交叉熵，保留梯度。"],
        "images = texts = torch.eye(2)\n"
        "temperature = 1.0\n"
        "→ tensor(0.313262)",
        '''
        import torch


        def clip_loss(images, texts, temperature):
            # images and texts: [B, D]
            pass
        ''',
        "相似度矩阵的对角线是正例。同一个 target 可以给相似度矩阵及其转置使用。",
        "先算所有图文对的余弦相似度。沿行的 CE 训练图像检索文本，沿列的 CE 训练反方向。",
        '''
        import torch
        import torch.nn.functional as F


        def clip_loss(images, texts, temperature):
            image_norm = F.normalize(images, dim=-1, eps=1e-12)
            text_norm = F.normalize(texts, dim=-1, eps=1e-12)
            scores = (image_norm @ text_norm.transpose(0, 1)) / temperature
            target = torch.arange(scores.shape[0], device=scores.device)
            return (F.cross_entropy(scores, target) + F.cross_entropy(scores.T, target)) / 2
        ''',
        [("两个完美匹配的样本", "(torch.eye(2), torch.eye(2), 1.0)"),
         ("不同尺度与温度", "(seq(3, 5) * 3., seq(3, 5).flip(0) + 2., 0.2)"),
         ("出现零向量", "(torch.tensor([[0., 0.], [1., 3.]]), torch.eye(2), 0.8)"),
         ("只含一个正样本", "(seq(1, 4), -seq(1, 4), 0.01)"),
         ("双向梯度", "(seq(4, 3).requires_grad_(), (seq(4, 3).flip(0) + 0.4).requires_grad_(), 0.3)")],
    ),
    exercise(
        "recent-window", "Bounded Frame Buffer", "入门", "Python", "流式记忆",
        "视频帧可能来自只能迭代一次的生成器。实现一个固定容量的最近帧缓冲区，按从早到晚返回最终保留的帧。",
        ["events 为可迭代对象，元素按到达次序给出。capacity 为非负整数。",
         "返回最近 min(元素总数, capacity) 个元素组成的 list。capacity 为 0 时返回空列表。",
         "可使用 Python 标准库。遍历一次，额外空间随 capacity 增长。"],
        "events = iter(['f0', 'f1', 'f2', 'f3'])\n"
        "capacity = 2\n"
        "→ ['f2', 'f3']",
        '''
        def recent_frames(events, capacity):
            # events may be a generator.
            pass
        ''',
        "collections.deque 有 maxlen 参数，队列满时追加新元素会自动丢掉最旧元素。",
        "有界队列在处理每个元素时只保留最近的 capacity 个元素。遍历 O(N)，额外空间 O(capacity)。",
        '''
        from collections import deque


        def recent_frames(events, capacity):
            if capacity == 0:
                return []
            return list(deque(events, maxlen=capacity))
        ''',
        [("生成器超过容量", "(iter(['f0', 'f1', 'f2', 'f3']), 2)"),
         ("视频短于容量", "(iter([(1, 'a'), (2, 'b')]), 5)"),
         ("空帧序列", "(iter(()), 5)"),
         ("零容量", "(iter(range(12)), 0)"),
         ("长序列只读一次", "((i % 7 for i in range(12001)), 4)")],
    ),
    exercise(
        "slot-update", "Gated Slot Update", "入门", "PyTorch", "流式记忆",
        "把每帧的新候选特征写入固定数量的记忆 slots。每个 slot 有自己的写入率，同时可以通过有效位阻止写入。",
        ["memory、candidate 为 [B, S, D]，rate、valid 为 [B, S]。",
         "rate 在 [0, 1]，valid 是布尔值。有效 slot 的新值为 (1-rate)·memory + rate·candidate。",
         "无效 slot 复制旧值。输出与 memory 同形状，输入可复用。",
         "用向量化的张量操作实现。"],
        "memory = [[[2., 4.], [1., 8.]]]\n"
        "candidate = [[[6., 0.], [3., 4.]]]\n"
        "rate = [[0.25, 1.]], valid = [[True, False]]\n"
        "→ [[[3., 3.], [1., 8.]]]",
        '''
        import torch


        def update_memory(memory, candidate, rate, valid):
            # Return the updated memory without mutating the inputs.
            pass
        ''',
        "用 rate.unsqueeze(-1) 为 feature 维度补一个可广播的轴，再用 valid 选择更新后的值。",
        "每个 rate 标量为整个 slot 的 D 个元素共享。先生成候选更新，再用布尔 mask 选择哪些 slot 真正写入。",
        '''
        import torch


        def update_memory(memory, candidate, rate, valid):
            weight = rate.unsqueeze(-1)
            update = (1 - weight) * memory + weight * candidate
            return torch.where(valid.unsqueeze(-1), update, memory)
        ''',
        [("部分写入与屏蔽", "(torch.tensor([[[2., 4.], [1., 8.]]]), torch.tensor([[[6., 0.], [3., 4.]]]), torch.tensor([[0.25, 1.]]), torch.tensor([[True, False]]))"),
         ("零写入与完全覆盖", "(seq(1, 3, 4), -seq(1, 3, 4), torch.tensor([[0., 1., 0.5]]), torch.ones(1, 3, dtype=torch.bool))"),
         ("多 batch 广播", "(seq(2, 4, 5), seq(2, 4, 5).flip(-1), torch.linspace(0., 1., 8).reshape(2, 4), torch.arange(8).reshape(2, 4) % 2 == 0)"),
         ("填充 slot 的候选为 NaN", "(seq(1, 2, 3), torch.full((1, 2, 3), torch.nan), torch.ones(1, 2), torch.zeros(1, 2, dtype=torch.bool))")],
    ),
    exercise(
        "gate-calibration", "Calibrate a Write Gate", "挑战", "PyTorch", "流式记忆",
        "在不改变各 slot 写入率排序的前提下，调整整组 gate 的平均写入率。对所有 logits 加同一个标量 bias。",
        ["logits 是非空一维 float64 张量，元素在 [-1000, 1000]，target 在 [0.00001, 0.99999]。",
         "返回 Python float b，使 mean(sigmoid(logits + b)) 与 target 的误差不超过 1e-7。",
         "使用单调搜索。考虑 logits 跨度大以及目标接近边界的情况。"],
        "logits = torch.zeros(3, dtype=torch.float64)\n"
        "target = 0.25\n"
        "→ b ≈ -1.098612",
        '''
        import torch


        def calibrate_gate(logits, target):
            # Return a scalar bias.
            pass
        ''',
        "平均 sigmoid 随 b 单调递增。用 target 的 logit 和输入的最大、最小值构造二分边界。",
        "令 c=logit(target)。取 b=c-max(logits) 时每一项都不高于 target，取 b=c-min(logits) 时每一项都不低于 target。",
        '''
        import math
        import torch


        def calibrate_gate(logits, target):
            center = math.log(target) - math.log1p(-target)
            lo = center - logits.max().item()
            hi = center - logits.min().item()
            for _ in range(48):
                mid = (lo + hi) / 2
                if torch.sigmoid(logits + mid).mean().item() < target:
                    lo = mid
                else:
                    hi = mid
            return (lo + hi) / 2
        ''',
        [("均匀写入率", "(torch.zeros(3, dtype=torch.float64), 0.25)"),
         ("混合 logits", "(torch.tensor([-2., 0.5, 4.], dtype=torch.float64), 0.7)"),
         ("幅度超过常用搜索边界", "(torch.tensor([995., 999., 1000.], dtype=torch.float64), 0.45)"),
         ("接近零的目标", "(torch.tensor([-700., 2., 500.], dtype=torch.float64), 0.00001)"),
         ("接近一的目标", "(torch.tensor([-1000., -998., -9., 1000.], dtype=torch.float64), 0.99999)")],
    ),
]

def load_sets(paths):
    for path in paths:
        for block in path.read_text(encoding="utf-8").split("\n@@ "):
            block = block.removeprefix("@@ ").strip()
            if not block:
                continue
            description, body, tests = block.split("\n---\n")
            heading, signature, summary, *notes = description.splitlines()
            id, title, level, topic, language = heading.split(" | ")
            rules, hint = notes[:-1], notes[-1].removeprefix("? ")
            runtime = {"N": "NumPy", "P": "Python"}[language]
            imports = "import numpy as np\n\n\n" if runtime == "NumPy" else ""
            starter = f"{imports}def {signature}:\n    pass\n"
            solution = f"{imports}def {signature}:\n{body.rstrip()}\n"
            cases = []
            for line in tests.splitlines():
                name, fixture = line.split(" | ", 1)
                args, _, expected = fixture.partition(" => ")
                cases.append((name, args, expected or None))
            example = signature.split("(")[0] + cases[0][1] + "\n→ " + (cases[0][2] or "运行以查看匹配结果")
            if runtime == "NumPy":
                example = re.sub(r"(?<![\w.])a\(", "np.array(", example)
            yield exercise(id, title, level, runtime, topic, summary, rules, example,
                           starter, hint, hint, solution, cases)


PROBLEMS.extend(load_sets(sorted(Path(__file__).with_name("sets").glob("*.txt"))))
BY_ID = {problem["id"]: problem for problem in PROBLEMS}
if len(BY_ID) != len(PROBLEMS):
    raise ValueError("Duplicate exercise identifiers")
PUBLIC_FIELDS = ("id", "title", "level", "runtime", "topic", "summary", "rules", "example", "starter", "hint", "explanation", "solution")


def catalog(problems=PROBLEMS):
    return [
        dict({key: p[key] for key in PUBLIC_FIELDS}, total=len(p["cases"]),
             previews=[case.name for case in p["cases"][:2]])
        for p in problems
    ]
