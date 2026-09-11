from __future__ import annotations
import re
from dataclasses import dataclass
from enum import IntEnum
class Sensitivity(IntEnum):
    PUBLIC=0; INTERNAL=1; CONFIDENTIAL=2; SECRET=3
_PATTERNS={Sensitivity.SECRET:[r'-----BEGIN [A-Z ]+PRIVATE KEY-----',r'\b(?:sk|ghp|github_pat|xox[baprs])_[A-Za-z0-9_-]{12,}',r'(?i)\b(?:password|passwd|secret|api[_ -]?key|token)\s*[:=]\s*[^\s]{8,}'],Sensitivity.CONFIDENTIAL:[r'\b\d{3}-\d{2}-\d{4}\b',r'\b(?:\d[ -]*?){13,19}\b',r'(?i)\b(?:private|confidential|internal[- ]only)\b'],Sensitivity.INTERNAL:[r'(?i)\b(?:proprietary|unreleased|non-public|私有|内部|未发布)\b']}
@dataclass(frozen=True)
class Finding: level:Sensitivity; label:str; start:int; end:int
@dataclass(frozen=True)
class Assessment:
    level:Sensitivity; findings:tuple[Finding,...]; route:str; redacted_text:str
    @property
    def external_allowed(self): return self.route=='external_allowed'
def assess(text:str)->Assessment:
    fs=[]
    for level,patterns in _PATTERNS.items():
        for p in patterns:
            fs.extend(Finding(level,p,m.start(),m.end()) for m in re.finditer(p,text))
    level=max((f.level for f in fs),default=Sensitivity.PUBLIC)
    route={0:'external_allowed',1:'local_preferred',2:'local_only',3:'block_external'}[level]
    red=text
    for f in sorted(fs,key=lambda x:x.start,reverse=True):
        if f.level>=Sensitivity.CONFIDENTIAL: red=red[:f.start]+'[REDACTED]'+red[f.end:]
    return Assessment(level,tuple(fs),route,red)
