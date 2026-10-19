# 复现记录

每条都是**独立可跑**的最小脚本。前半段在未修复的基线（`baseline/`）上跑，后半段在同一份脚本上跑修复后的源码（`src/`），输出即为对照证据。

环境：Windows 11 / Python 3.13.14。POSIX 平台行为一致（见 `evidence/cross_platform.py`）。

---

## 前置

```bash
# 先装本包：test_cli.py 会以子进程方式调用 dotenv 命令行入口。
# 不装的话 20 个 CLI 用例会报 FileNotFoundError —— 那是环境问题，不是包的问题。
pip install -e .

# 未修复基线（= 上游 commit 0b28805 的 git archive 导出）
cd baseline && pytest tests -q
# 235 passed, 0 failed, 50 skipped

# 修复后
cd .. && pytest tests -q
# 306 passed, 0 failed, 50 skipped
```

> 50 个 skip 是上游自己的 POSIX-only 用例（符号链接 / FIFO / `chmod` / `tzset`），
> Windows 上按设计跳过。这些行为改用 `evidence/cross_platform.py` 做字节级断言覆盖。

---

## 1. CRLF 下错误恢复只消费 `\r`

```bash
cd baseline && PYTHONPATH=src python ../evidence/probe_lines.py
```

```
CRLF  warnings=['...starting at line 2', '...starting at line 5']   ← 应为 2 和 4
      line=2 err=True orig='=bad\r'
      line=3 err=False orig='\nB=2\r\n'        ← 前导 \n 被算进下一行
```

```bash
cd ../src/.. && PYTHONPATH=src python evidence/probe_lines.py
```

```
CRLF  warnings=['...starting at line 2', '...starting at line 4']
      line=2 err=True orig='=bad\r\n'          ← 完整终止符
      line=3 err=False orig='B=2\r\n'
```

**断言**：`tests/test_parser.py::test_parse_stream_recovers_whole_line_on_invalid_statement[\r\n]`

---

## 2. `rewrite()` 转换整文件行尾

```bash
PYTHONPATH=src python evidence/probe_eol.py      # 在 baseline 与 src 下各跑一次
```

| 输入 | 操作 | 基线 | 修复后 |
|------|------|------|--------|
| `A=1\nB=2\nC=3\n` | set C | `A=1\r\nB=2\r\nC='9'\r\n` | `A=1\nB=2\nC='9'\n` |
| `A=1\r\nB=2\r\nC=3\r\n` | unset A | 行尾按 `os.linesep` 全量重写 | 保持 CRLF |
| `A=1\rB=2\rC=3\r` | set C | 全变 CRLF | 保持 CR |
| `BOM+LF` | set C | BOM 丢失 + 全变 CRLF | BOM 保留 + LF 不变 |

**断言**：`test_set_key_preserves_line_endings[*]`、`test_set_key_appends_with_the_last_line_terminator[*]`

---

## 3. BOM 被丢弃

```bash
PYTHONPATH=src python -c "
import tempfile, os
from dotenv import set_key, unset_key
p = os.path.join(tempfile.mkdtemp(), '.env')
open(p,'wb').write(b'\xef\xbb\xbfA=1\nB=2\n')
set_key(p,'C','9')
print('set  :', open(p,'rb').read())
open(p,'wb').write(b'\xef\xbb\xbfA=1\nB=2\n')
unset_key(p,'A')
print('unset:', open(p,'rb').read())
"
```

```
基线  : set   b"A=1\r\nB=2\r\nC='9'\r\n"
        unset b'B=2\r\n'
修复后: set   b"\xef\xbb\xbfA=1\nB=2\nC='9'\n"
        unset b'\xef\xbb\xbfB=2\n'
```

**断言**：`test_set_key_preserves_bom`、`test_unset_key_preserves_bom`、`test_unset_key_keeps_bom_when_key_is_missing`

---

## 4. 值里的 `\r` 读回变 `\n`

```bash
PYTHONPATH=src python -c "
import tempfile, os
from dotenv import set_key, get_key
p = os.path.join(tempfile.mkdtemp(), '.env')
for v in ['a\rb', 'a\r\nb']:
    set_key(p, 'K', v)
    print(repr(v), '->', repr(get_key(p, 'K')))
"
```

```
基线  : 'a\rb'   -> 'a\nb'
        'a\r\nb' -> 'a\n\nb'
修复后: 'a\rb'   -> 'a\rb'
        'a\r\nb' -> 'a\r\nb'
```

**断言**：`test_set_key_round_trips_carriage_returns[*]`、`test_dotenv_values_preserves_carriage_returns[*]`

---

## 5. CLI 编码与写入端不一致

```bash
# 真实子进程，locale=cp936（中文 Windows 控制台）
PYTHONUTF8=0 PYTHONIOENCODING=utf-8 python -m dotenv -f /tmp/x.env set GREETING 你好
PYTHONUTF8=0 PYTHONIOENCODING=utf-8 python -m dotenv -f /tmp/x.env get GREETING
```

```
基线  : set  -> GREETING=你好      (文件里是 UTF-8)
        get  -> 浣犲ソ              ← GBK 解 UTF-8
        含 😀 时 list 直接 UnicodeDecodeError + traceback + rc=1
修复后: get  -> 你好                rc=0
        不可解码文件 -> "Error decoding env file: ..." + rc=2，无 traceback
```

**断言**：`test_stream_file_decodes_as_utf8`（结构性：断言传给 `open` 的 `encoding == "utf-8"`）、`test_cli_round_trips_non_ascii_under_a_gbk_process_locale`、`test_list_reports_undecodable_file_without_a_traceback`

> 为什么用结构性断言：`open()` 在 C 层解析 locale，`monkeypatch.setattr(locale, "getpreferredencoding", ...)` **不生效**（实测过，行为测试在 UTF-8 CI 机器上会假绿）。真正能抓 bug 的是 GBK 子进程那条。

---

## 6. `set_key` 不校验 key

```bash
PYTHONPATH=src python evidence/probe_key.py
```

```
基线：
  key='A B'   file="BASE=1\nA B='v'\n"     read_back={'BASE': '1'}            ← key 丢了
  key='A=B'   file="BASE=1\nA=B='v'\n"     read_back={'BASE': '1', 'A': "B='v'"}  ← 变成 A
  key='A#B'   file="BASE=1\nA#B='v'\n"     read_back={'BASE': '1', 'A': None}
  key='A\nB'  file="BASE=1\nA\nB='v'\n"    read_back={'BASE': '1', 'A': None, 'B': 'v'}
  全部 return (True, key, value)

修复后：以上全部 ValueError，文件保持 b"BASE=1\n"
  key='中文键' / 'A-B' / 'A.B' / '1' / '_x'  仍然 OK
```

**断言**：`test_set_key_rejects_unwritable_key[*]`（9 条）、`test_set_key_accepts_writable_key[*]`（6 条）、`test_set_rejects_key_the_parser_cannot_read_back`

---

## 7. `${name:-default}` 对空值不生效

```bash
PYTHONPATH=src python -c "
import io
from dotenv import dotenv_values
for s in ['b=\na=\${b:-d}\n', 'b\na=\${b:-d}\n', 'b=0\na=\${b:-d}\n']:
    print(repr(s), '->', dict(dotenv_values(stream=io.StringIO(s))))
"
```

```
基线  : 'b=\na=${b:-d}\n'   -> {'b': '', 'a': ''}       ← 应为 'd'
        'b\na=${b:-d}\n'    -> {'b': None, 'a': ''}     ← 应为 'd'
        'b=0\na=${b:-d}\n'  -> {'b': '0', 'a': '0'}
修复后: {'b': '', 'a': 'd'} / {'b': None, 'a': 'd'} / {'b': '0', 'a': '0'}
```

**断言**：`test_variable_resolve_default_semantics[*]`（含 `{"b": "0"}` → `"0"`，锁住「只有空串算 null」）、`test_dotenv_values_uses_default_for_empty_values[*]`

---

## 8. 裸声明遮蔽环境变量

```bash
PYTHONPATH=src python evidence/probe_mask.py
```

```
基线  : 'MASKVAR\nB=${MASKVAR}\n'  override=True -> {'MASKVAR': None, 'B': ''}
修复后:                                              {'MASKVAR': None, 'B': 'fromenv'}
```

**断言**：`test_bare_declaration_does_not_mask_the_environment_in_expansion`

---

## 9. `load_dotenv()` 返回值

```bash
PYTHONPATH=src python evidence/probe_ret.py
```

```
基线  : only bare keys          -> return=True   environ={}      ← 契约不符
修复后: only bare keys          -> return=False  environ={}
        bare + empty value      -> return=True   environ={'B': ''}
        bare + real value       -> return=True   environ={'B': '1'}
        empty file / only comment -> return=False
        all skipped by no-override -> return=True（原有语义，未改）
```

**断言**：`test_load_dotenv_return_value_means_a_variable_was_set[*]`

---

## 10. `parse_variables` 二次复杂度

```bash
PYTHONPATH=src python evidence/probe_q2.py      # 在 baseline 下跑
```

```
A: ${ xN, no brace at all
   n= 1000 chars=   2000     26.98 ms
   n= 2000 chars=   4000    107.78 ms  3.99x
   n= 4000 chars=   8000    440.46 ms  4.09x
   n= 8000 chars=  16000   1712.80 ms  3.89x     ← 每翻倍 ×4
```

修复后同脚本：`0.04 / 0.06 / 0.12 / 0.25 ms`（每翻倍 ×2）。

经 `load_dotenv` 可达：8000 字符恶意值 0.51 s，32 KB 约 8 s。

**断言**：`test_parse_variables_is_linear_on_unterminated_expansions`（基线上 4 倍输入对应 ~16–19 倍耗时，触发 `large_elapsed < small_elapsed * 10 + 0.05`）

---

## 附：等价性证据（缺陷 10 的修复没有改语义）

```bash
python evidence/probe_diff2.py
```

```
corpus=120250 differing=0
```

对照：把 name 字符类改成 `[^\}:$]*` 的「取巧版」在同一语料上是 **293 条差异**（`${a$b}` 的解析结果变了），已回退。
