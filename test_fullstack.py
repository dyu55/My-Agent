#!/usr/bin/env python3
"""Hard full-stack test v2: 12 steps with complex parameters.
Multi-provider: Ollama Cloud (3 models) + DeepSeek API (v4-flash)."""

import os, sys, time, json
from datetime import datetime

os.chdir('/Users/donglingyu/Documents/MyAgent')
from dotenv import load_dotenv
load_dotenv()
from utils.model_provider import ModelManager, ModelProviderFactory

# ============================================================
# MODELS
# ============================================================
MODELS = [
    # Ollama Cloud models (free tier)
    ('ollama', 'gemma4:31b', 'gemma4-31b', '62GB Google'),
    ('ollama', 'nemotron-3-nano:30b', 'nemotron-nano', '32GB NVIDIA'),
    ('ollama', 'qwen3-coder-next', 'qwen3-coder', '81GB Alibaba'),
    # DeepSeek API
    ('deepseek', 'deepseek-v4-flash', 'v4-flash', 'DeepSeek Flash'),
]

# ============================================================
# 12 HARD STEPS — B站 clone, 初二学生视角
# ============================================================
STEPS = [
    {
        "id": "step_01_ambition",
        "prompt": """你好！我今年初二，第一次接触编程。我想做一个像B站那样的视频网站！功能包括：用户注册登录、上传视频、弹幕、点赞收藏关注、评论、搜索。同学说做网站要用Spring Boot和React，你能教我从零搭建吗？我只有IntelliJ IDEA。""",
        "checks": ["Spring Boot", "React", "项目结构", "入门引导", "pom.xml"],
    },
    {
        "id": "step_02_db_design",
        "prompt": """帮我设计数据库。要有：用户表（含头像、简介、粉丝数、关注数）、视频表（标题、描述、封面、播放量、状态审核）、弹幕表、评论表（支持嵌套回复）、点赞表（区分视频点赞和评论点赞）、收藏夹表、关注关系表。写完整DDL，每个字段中文注释，要有索引设计。""",
        "checks": ["CREATE TABLE", "FOREIGN KEY", "INDEX", "COMMENT", "AUTO_INCREMENT"],
    },
    {
        "id": "step_03_entity_jpa",
        "prompt": """写Spring Boot的Entity。需要：User、Video、Danmaku、Comment、Like、Favorite、Follow 一共7个Entity类。用JPA注解：@Entity @Table @Id @GeneratedValue @Column @ManyToOne @OneToMany @JoinColumn。要有@CreatedDate和@LastModifiedDate审计字段。再写对应的7个JpaRepository接口，包含自定义查询方法（如findByVideoIdOrderByCreateTimeDesc）。""",
        "checks": ["@Entity", "@ManyToOne", "@OneToMany", "JpaRepository", "@CreatedDate"],
    },
    {
        "id": "step_04_video_api",
        "prompt": """写视频Service和Controller。功能：上传视频（校验文件大小<500MB、格式MP4/AVI/MKV）、获取视频列表（分页+排序：按时间/播放量/点赞数）、视频详情（含作者信息、点赞收藏状态、前10条热评）、搜索（标题模糊+标签筛选）、编辑视频信息、删除（软删除，标记status=DELETED）、增加播放量（防刷，同一IP 30分钟内只算1次）。每段代码加注释。DTO和VO分开。""",
        "checks": ["@RestController", "@Service", "Pageable", "软删除", "防刷", "DTO"],
    },
    {
        "id": "step_05_jwt_security",
        "prompt": """安全认证。需求：JWT登录（accessToken 2小时 + refreshToken 7天）、注册（密码BCrypt加密+邮箱验证码）、Spring Security配置（放行登录注册+其他全部鉴权）、角色权限（ROLE_USER / ROLE_ADMIN / ROLE_CREATOR 三级）、自定义注解@RequireRole用于Controller方法级别控制、全局异常处理@RestControllerAdvice。写完整代码。""",
        "checks": ["JWT", "BCrypt", "Spring Security", "@RequireRole", "@RestControllerAdvice", "refreshToken"],
    },
    {
        "id": "step_06_react_pages",
        "prompt": """React前端。Vite创建项目，用：React Router v6（路由懒加载lazy）、Axios（拦截器自动带token+401跳转登录）、Zustand状态管理、Ant Design组件库。页面：首页（视频卡片网格+无限滚动IntersectionObserver）、视频详情（播放器+弹幕层+评论树形嵌套）、登录注册（表单验证）、个人中心（投稿管理+收藏夹）、创作者后台（数据看板ECharts图表）。写完整JSX。""",
        "checks": ["React Router", "Axios", "Zustand", "Ant Design", "IntersectionObserver", "ECharts"],
    },
    {
        "id": "step_07_danmaku_websocket",
        "prompt": """弹幕系统。后端：Spring WebSocket + STOMP协议，弹幕存Redis（Sorted Set按时间戳），定时批量刷入MySQL。前端：Canvas绘制弹幕引擎（弹幕碰撞检测避免重叠、不同颜色、速度分级、透明度）、用户发送弹幕（限制5秒1条防刷）。WebSocket心跳保活+断线重连。写完整前后端代码。""",
        "checks": ["WebSocket", "STOMP", "Canvas", "碰撞检测", "Redis", "心跳"],
    },
    {
        "id": "step_08_chunked_upload",
        "prompt": """视频上传要大文件支持！改成：前端用SparkMD5计算文件hash + slice分片（每片5MB），并发上传3片。后端接口：initUpload（返回uploadId）、uploadChunk（校验hash）、mergeChunks（合并分片）、checkProgress（查询已上传分片列表，支持断点续传）。合并完成后用FFmpeg转码生成多清晰度（1080p/720p/480p）。写完整代码。""",
        "checks": ["分片上传", "SparkMD5", "断点续传", "FFmpeg", "并发上传", "uploadId"],
    },
    {
        "id": "step_09_redis_cache",
        "prompt": """性能优化。用Redis做：视频详情缓存（Cache-Aside模式，防止缓存雪崩：随机过期时间+互斥锁）、热门视频排行榜（ZSet，每小时更新）、布隆过滤器防缓存穿透（Guava BloomFilter初始化100万容量）、用户Session管理（登录状态缓存）、接口限流（基于IP的令牌桶算法，每秒100请求）。同时写Spring Cache配置（@Cacheable、@CacheEvict、@CachePut）。""",
        "checks": ["Cache-Aside", "互斥锁", "布隆过滤器", "令牌桶", "ZSet", "@Cacheable"],
    },
    {
        "id": "step_10_testing",
        "prompt": """帮我写测试！单元测试：VideoService的每个方法（JUnit5 + Mockito，mock Repository和Redis）、UserController的登录注册（MockMvc测试）。集成测试：完整的视频上传→审核→发布→搜索流程（@SpringBootTest + TestContainers启动真实MySQL和Redis）。测试覆盖率要求>80%。每段测试代码加@DisplayName中文描述。""",
        "checks": ["JUnit5", "Mockito", "MockMvc", "@SpringBootTest", "TestContainers", "@DisplayName"],
    },
    {
        "id": "step_11_docker",
        "prompt": """容器化部署。写：Dockerfile（多阶段构建：maven打包 + OpenJDK运行，用非root用户）、docker-compose.yml（MySQL 8.0 + Redis 7 + MinIO对象存储 + Nginx + Spring Boot应用 + React前端Nginx静态）、各服务的健康检查healthcheck、数据卷挂载、网络隔离（backend/frontend两个网络）。还要一个docker-deploy.sh一键部署脚本。""",
        "checks": ["Dockerfile", "docker-compose", "多阶段构建", "healthcheck", "非root", "MinIO"],
    },
    {
        "id": "step_12_monitoring",
        "prompt": """最后加监控和日志！集成：Prometheus + Grafana（JVM指标、API QPS/延迟、数据库连接池）、Spring Boot Actuator暴露metrics端点、ELK日志收集（Logback输出JSON格式→Filebeat→Elasticsearch→Kibana）、自定义业务埋点（视频上传成功率、弹幕发送延迟P99）。写完整的配置文件和接入指南。""",
        "checks": ["Prometheus", "Grafana", "Actuator", "ELK", "Logback", "自定义埋点"],
    },
]

def log(msg):
    print(msg)
    sys.stdout.flush()

def run_step(manager, step, conversation_history):
    """Run one conversation step."""
    prompt = step['prompt']
    full_prompt = prompt

    if conversation_history:
        context_brief = "\n\n".join(
            f"[上一步: {h['id']}，已回答约{h['len']}字符]\n{h['summary'][:200]}"
            for h in conversation_history[-3:]
        )
        full_prompt = f"之前的对话摘要：\n{context_brief}\n\n现在的新问题：\n{prompt}"

    for attempt in range(3):
        try:
            start = time.time()
            response = manager.chat(full_prompt, timeout=300)
            elapsed = time.time() - start

            checks_hit = []
            for check in step['checks']:
                if check.lower() in response.lower():
                    checks_hit.append(check)

            return {
                'step_id': step['id'],
                'success': True,
                'elapsed': round(elapsed, 2),
                'length': len(response),
                'response_summary': response[:300],
                'checks_hit': checks_hit,
                'checks_total': len(step['checks']),
                'error': '',
            }
        except Exception as e:
            err = str(e)
            log(f"  Attempt {attempt+1}: {err[:150]}")
            time.sleep(10 if 'rate' not in err.lower() else 60)

    return {'step_id': step['id'], 'success': False, 'error': 'Failed after 3 attempts'}

def main():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log('=' * 70)
    log('FULL-STACK v2 — 12 HARD STEPS × 4 MODELS')
    log('Spring Boot + React (B站克隆) | 初二学生视角')
    log('=' * 70)
    log(f'Models: gemma4:31b | nemotron-nano | qwen3-coder | deepseek-v4-flash')
    log(f'Steps: {len(STEPS)} | Total checks: {sum(len(s["checks"]) for s in STEPS)}')
    log('')

    all_results = {}
    total_steps = len(STEPS)

    for provider, model_name, model_id, model_desc in MODELS:
        log(f'\n{"="*50}')
        log(f'MODEL: {model_name}  ({model_desc})  provider={provider}')
        log(f'{"="*50}')

        manager = ModelManager()
        manager.set_model(provider, model_name)
        log(f'Health: {manager.health_check()}')

        model_results = {'provider': provider, 'model': model_name,
                         'desc': model_desc, 'steps': [], 'summary': {}}
        conversation_history = []

        for i, step in enumerate(STEPS):
            log(f'\n[{i+1}/{total_steps}] {step["id"]}')
            prompt_preview = step["prompt"][:100].replace('\n', ' ')
            log(f'  用户: "{prompt_preview}..."')

            result = run_step(manager, step, conversation_history)
            model_results['steps'].append(result)

            if result['success']:
                checks = f"{len(result['checks_hit'])}/{result['checks_total']}"
                log(f'  ✅ {result["elapsed"]}s | {result["length"]} chars | checks: {checks}')
                conversation_history.append({
                    'id': step['id'],
                    'summary': result['response_summary'],
                    'len': result['length'],
                })
            else:
                log(f'  ❌ {result.get("error", "unknown")[:80]}')
                break

            time.sleep(3)

        # Summary
        ok = [s for s in model_results['steps'] if s['success']]
        if ok:
            avg_t = sum(s['elapsed'] for s in ok) / len(ok)
            avg_l = sum(s['length'] for s in ok) / len(ok)
            hit = sum(len(s['checks_hit']) for s in ok)
            max_chk = sum(s['checks_total'] for s in ok)
        else:
            avg_t = avg_l = hit = max_chk = 0

        model_results['summary'] = {
            'steps_ok': len(ok), 'steps_total': len(STEPS),
            'avg_time_s': round(avg_t, 1), 'avg_length': round(avg_l, 0),
            'checks_hit': hit, 'checks_total': max_chk,
        }

        all_results[model_id] = model_results

        with open(f'logs/fullstack_v2_{timestamp}.json', 'w') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)

        log(f'\n--- {model_name}: {len(ok)}/{total_steps} steps | '
            f'avg {avg_t:.1f}s | {avg_l:.0f} chars | checks {hit}/{max_chk} ---')

        if model_id != MODELS[-1][2]:
            log('\n  ⏳ 30s pause...')
            time.sleep(30)

    # Final sweep
    log('\n' + '=' * 70)
    log('FINAL RESULTS')
    log('=' * 70)

    for _, model_name, model_id, model_desc in MODELS:
        r = all_results.get(model_id, {})
        s = r.get('summary', {})
        log(f'\n{model_id:20s} ({model_desc})')
        log(f'  Steps:   {s.get("steps_ok", 0)}/{s.get("steps_total", 0)}')
        log(f'  Avg time:{s.get("avg_time_s", 0)}s')
        log(f'  Avg len: {s.get("avg_length", 0)} chars')
        log(f'  Checks:  {s.get("checks_hit", 0)}/{s.get("checks_total", 0)}')

    log(f'\n📁 logs/fullstack_v2_{timestamp}.json')

if __name__ == '__main__':
    main()
