import requests
import time
import sys
import re
import os
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote

# ============================================================
# ⚙️ 사용자 설정: 여기에 본인의 파이어베이스 주소를 적어주세요!
# ============================================================
FIREBASE_DB_URL = "https://blog-aaa78-default-rtdb.asia-southeast1.firebasedatabase.app/" 
# 예시: "https://my-wordbook.firebaseio.com/"
# ============================================================


# 순수 정적 파일로 재탄생한 index.html 템플릿 (데이터 포함 X)
STATIC_INDEX_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>나만의 단어장 (Cloud Sync)</title>
    <script src="id/_id_list.js"></script>
    <style>
        body { font-family: 'Malgun Gothic', sans-serif; margin: 0; padding: 0; display: flex; height: 100vh; background-color: #f4f6f8; overflow: hidden; }
        .sidebar { width: 35%; background: #ffffff; border-right: 1px solid #ddd; display: flex; flex-direction: column; }
        .sidebar-header { padding: 20px; border-bottom: 2px solid #3498db; }
        .btn { padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        .btn-edit { background-color: #f39c12; color: white; }
        .btn-back { background-color: #95a5a6; color: white; margin-right: 10px; }
        .btn-delete { background-color: #e74c3c; color: white; display: none; margin-left: 10px; }
        .sync-status { font-size: 12px; color: #2ecc71; margin-top: 10px; font-weight: bold; }
        .list-container { overflow-y: auto; padding: 20px; flex-grow: 1; }
        .post-item, .blog-item { display: flex; align-items: center; padding: 12px 15px; margin-bottom: 8px; background: #eaf2f8; border-radius: 6px; }
        .blog-item { background: #fdf2e3; border-left: 4px solid #f39c12; }
        .post-title { flex-grow: 1; cursor: pointer; font-weight: bold; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .blog-name { flex-grow: 1; cursor: pointer; font-weight: bold; font-size: 16px; }
        .blog-count { font-size: 12px; color: #7f8c8d; margin-left: 8px; white-space: nowrap; }
        .delete-checkbox { display: none; margin-right: 10px; }
        .main-content { width: 65%; display: flex; flex-direction: column; background: white; }
        .header-bar { padding: 15px; background: #ecf0f1; border-bottom: 1px solid #ddd; display: flex; justify-content: space-between; align-items: center; }
        #content-frame { flex-grow: 1; width: 100%; border: none; }
        .post-title[contenteditable="true"], .blog-name[contenteditable="true"] { cursor: text; white-space: normal; background: #fffbe6; outline: 2px dashed #f39c12; border-radius: 4px; padding: 2px 4px; }
        #content-edit { flex-grow: 1; width: 100%; padding: 20px; overflow-y: auto; box-sizing: border-box; line-height: 1.6; }
        #content-edit[contenteditable="true"] { background: #fffbe6; outline: 2px dashed #f39c12; outline-offset: -2px; }
        .btn-content-edit { background-color: #16a085; color: white; }
        .btn-content-save { background-color: #2980b9; color: white; }
        .btn-content-cancel { background-color: #7f8c8d; color: white; }
        .empty-state { padding: 40px 20px; text-align: center; color: #95a5a6; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="display:flex; align-items:center;">
                    <button id="back-btn" class="btn btn-back" style="display:none;" onclick="goBackToBlogs()">← 목록</button>
                    <h2 id="sidebar-title" style="margin:0;">📚 단어장</h2>
                </div>
                <div>
                    <button id="edit-btn" class="btn btn-edit" onclick="toggleEditMode()">목록 편집</button>
                    <button id="delete-btn" class="btn btn-delete" onclick="deleteSelected()">숨기기</button>
                </div>
            </div>
            <div id="sync-status" class="sync-status">🔄 로딩 중...</div>
        </div>
        <div class="list-container">
            <ul class="post-list" id="post-list" style="list-style:none; margin:0; padding:0;"></ul>
        </div>
    </div>
    <div class="main-content">
        <div id="header-bar" class="header-bar" style="display:none;">
            <span id="header-title" style="font-weight:bold;"></span>
            <div>
                <a id="header-link" href="#" target="_blank" style="color:#3498db; text-decoration:none; font-weight:bold; margin-right:10px;">🔗 원본</a>
                <button id="content-edit-btn" class="btn btn-content-edit" onclick="toggleContentEdit()">✏️ 본문 편집</button>
                <button id="content-save-btn" class="btn btn-content-save" style="display:none;" onclick="saveContentEdit()">💾 서버에 저장</button>
                <button id="content-cancel-btn" class="btn btn-content-cancel" style="display:none;" onclick="cancelContentEdit()">취소</button>
            </div>
        </div>
        <iframe id="content-frame" style="display: none;"></iframe>
        <div id="content-edit" style="display:none;"></div>
    </div>
    
    <script>
        // 전역 데이터 배열
        window.blogsData = [];
        
        // 파이썬 설정값 치환
        const FIREBASE_URL = "__FIREBASE_DB_URL__"; 
        
        let isEditMode = false;
        let currentView = 'blogs';
        let currentBlogId = null;
        let currentContentId = null;
        let currentContentUrl = null;

        let dbData = { deleted_blogs: {}, deleted_posts: {}, content_overrides: {} };

        document.addEventListener('DOMContentLoaded', async function() { 
            await loadAllBlogDataFiles();
            await loadFirebaseData();
            renderBlogList(); 
        });

        // 2. _id_list.js에서 가져온 activeBlogIds를 바탕으로 개별 JS 파일들을 동적으로 불러옵니다.
        async function loadAllBlogDataFiles() {
            if (typeof activeBlogIds === 'undefined' || activeBlogIds.length === 0) {
                document.getElementById('sync-status').innerText = "📂 등록된 데이터가 없습니다.";
                return;
            }
            
            const promises = activeBlogIds.map(id => {
                return new Promise((resolve) => {
                    const script = document.createElement('script');
                    script.src = `id/${id}.js`;
                    script.onload = resolve;
                    script.onerror = () => {
                        console.warn(`${id}.js 파일을 찾을 수 없습니다. _id_list.js를 확인하세요.`);
                        resolve(); // 하나가 실패해도 나머지는 로드되도록 진행
                    };
                    document.head.appendChild(script);
                });
            });
            
            await Promise.all(promises);
        }

        async function loadFirebaseData() {
            if (!FIREBASE_URL || FIREBASE_URL === "__" + "FIREBASE_DB_URL" + "__") {
                document.getElementById('sync-status').innerText = "⚠️ 오프라인 모드";
                document.getElementById('sync-status').style.color = "#e74c3c";
                return;
            }
            try {
                let url = FIREBASE_URL;
                if (!url.endsWith('/')) url += '/';
                const res = await fetch(url + '.json');
                const data = await res.json() || {};
                dbData.deleted_blogs = data.deleted_blogs || {};
                dbData.deleted_posts = data.deleted_posts || {};
                dbData.content_overrides = data.content_overrides || {};
                
                document.getElementById('sync-status').innerText = "✅ 클라우드 동기화 완료";
            } catch (err) {
                console.error("Firebase 로드 오류", err);
                document.getElementById('sync-status').innerText = "❌ 클라우드 연결 실패";
                document.getElementById('sync-status').style.color = "#e74c3c";
            }
        }

        async function updateFirebase(path, value) {
            if (!FIREBASE_URL || FIREBASE_URL === "__" + "FIREBASE_DB_URL" + "__") return;
            try {
                let url = FIREBASE_URL;
                if (!url.endsWith('/')) url += '/';
                await fetch(url + path + '.json', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(value)
                });
            } catch(e) { console.error("Firebase 저장 오류", e); }
        }

        function escapeHtml(str) {
            const div = document.createElement('div');
            div.innerText = str;
            return div.innerHTML;
        }

        function renderBlogList() {
            currentView = 'blogs';
            currentBlogId = null;
            isEditMode = false;
            document.getElementById('back-btn').style.display = 'none';
            document.getElementById('sidebar-title').innerText = '📚 블로그 목록';
            document.getElementById('header-bar').style.display = 'none';
            document.getElementById('content-frame').style.display = 'none';
            document.getElementById('content-edit').style.display = 'none';
            updateEditButtons();

            const listEl = document.getElementById('post-list');
            listEl.innerHTML = '';
            
            const visibleBlogs = window.blogsData.filter(b => !dbData.deleted_blogs[b.id]);
            if (visibleBlogs.length === 0) {
                listEl.innerHTML = '<div class="empty-state">표시할 블로그가 없어요.</div>';
                return;
            }
            
            visibleBlogs.forEach(blog => {
                const deletedPostCount = dbData.deleted_posts[blog.id] ? Object.keys(dbData.deleted_posts[blog.id]).length : 0;
                const remainingCount = blog.posts.length - deletedPostCount;
                const li = document.createElement('li');
                li.className = 'blog-item';
                li.id = 'blog_' + blog.id;
                li.innerHTML = "<input type='checkbox' class='delete-checkbox' value='" + blog.id + "'> " +
                    "<span class='blog-name' onclick=\\"onBlogClick('" + blog.id + "')\\">" + escapeHtml(blog.name) + "</span>" +
                    "<span class='blog-count'>" + remainingCount + "개</span>";
                listEl.appendChild(li);
            });
        }

        function onBlogClick(blogId) { if (!isEditMode) selectBlog(blogId); }

        function selectBlog(blogId) {
            currentBlogId = blogId;
            renderPostList(blogId);
        }

        function renderPostList(blogId) {
            currentView = 'posts';
            currentBlogId = blogId;
            isEditMode = false;
            const blog = window.blogsData.find(b => b.id === blogId);
            if (!blog) return;
            document.getElementById('back-btn').style.display = 'inline-block';
            document.getElementById('sidebar-title').innerText = '📑 ' + blog.name;
            document.getElementById('header-bar').style.display = 'none';
            document.getElementById('content-frame').style.display = 'none';
            document.getElementById('content-edit').style.display = 'none';
            updateEditButtons();

            const listEl = document.getElementById('post-list');
            listEl.innerHTML = '';
            
            const visiblePosts = blog.posts.filter(p => !(dbData.deleted_posts[blogId] && dbData.deleted_posts[blogId][p.id]));
            if (visiblePosts.length === 0) {
                listEl.innerHTML = '<div class="empty-state">표시할 글이 없어요.</div>';
                return;
            }
            
            visiblePosts.forEach(post => {
                const isEdited = dbData.content_overrides[blogId] && dbData.content_overrides[blogId][post.id] ? " ✏️" : "";
                const li = document.createElement('li');
                li.className = 'post-item';
                li.id = post.id;
                li.innerHTML = "<input type='checkbox' class='delete-checkbox' value='" + post.id + "'> " +
                    "<div class='post-title' onclick=\\"onPostClick('" + blogId + "', '" + post.id + "')\\">" + escapeHtml(post.title) + isEdited + "</div>";
                listEl.appendChild(li);
            });
        }

        function onPostClick(blogId, postId) {
            if (isEditMode) return;
            const blog = window.blogsData.find(b => b.id === blogId);
            const post = blog ? blog.posts.find(p => p.id === postId) : null;
            loadContent(blogId, postId, post.title);
        }

        function loadContent(blogId, postId, displayTitle) {
            currentContentId = postId;
            currentBlogId = blogId;
            // 불러오는 경로를 source 폴더로 변경했습니다.
            currentContentUrl = 'source/' + blogId + '/' + postId + '.html';
            const blog = window.blogsData.find(b => b.id === blogId);
            const post = blog ? blog.posts.find(p => p.id === postId) : null;

            document.getElementById('header-bar').style.display = 'flex';
            document.getElementById('header-title').innerText = displayTitle;
            document.getElementById('header-link').href = post ? post.link : '#';

            const frame = document.getElementById('content-frame');
            const editDiv = document.getElementById('content-edit');
            editDiv.style.display = 'none';
            frame.style.display = 'block';

            const overrideHtml = dbData.content_overrides[blogId] && dbData.content_overrides[blogId][postId];
            if (overrideHtml) {
                frame.removeAttribute('src');
                frame.srcdoc = overrideHtml;
            } else {
                frame.removeAttribute('srcdoc');
                frame.src = currentContentUrl;
            }
            
            document.getElementById('content-edit-btn').style.display = 'inline-block';
            document.getElementById('content-save-btn').style.display = 'none';
            document.getElementById('content-cancel-btn').style.display = 'none';
        }

        async function toggleContentEdit() {
            if (!currentContentUrl) return;
            const editDiv = document.getElementById('content-edit');
            const frame = document.getElementById('content-frame');
            
            let html = dbData.content_overrides[currentBlogId] && dbData.content_overrides[currentBlogId][currentContentId];
            
            if (!html) {
                try {
                    const res = await fetch(currentContentUrl);
                    if (!res.ok) throw new Error('fetch failed');
                    html = await res.text();
                } catch (err) {
                    alert('원본 텍스트를 불러오지 못했습니다.');
                    return;
                }
            }
            
            editDiv.innerHTML = html;
            editDiv.setAttribute('contenteditable', 'true');
            frame.style.display = 'none';
            editDiv.style.display = 'block';
            
            document.getElementById('content-edit-btn').style.display = 'none';
            document.getElementById('content-save-btn').style.display = 'inline-block';
            document.getElementById('content-cancel-btn').style.display = 'inline-block';
            editDiv.focus();
        }

        async function saveContentEdit() {
            const editDiv = document.getElementById('content-edit');
            const newHtml = editDiv.innerHTML;
            
            document.getElementById('sync-status').innerText = "☁️ 클라우드 저장 중...";
            
            if (!dbData.content_overrides[currentBlogId]) dbData.content_overrides[currentBlogId] = {};
            dbData.content_overrides[currentBlogId][currentContentId] = newHtml;
            
            await updateFirebase(`content_overrides/${currentBlogId}/${currentContentId}`, newHtml);
            
            document.getElementById('sync-status').innerText = "✅ 클라우드 저장 완료";
            
            exitContentEditView(newHtml);
            renderPostList(currentBlogId); 
        }

        function cancelContentEdit() { 
            const html = dbData.content_overrides[currentBlogId] && dbData.content_overrides[currentBlogId][currentContentId];
            exitContentEditView(html); 
        }

        function exitContentEditView(overrideHtml) {
            const frame = document.getElementById('content-frame');
            const editDiv = document.getElementById('content-edit');
            editDiv.removeAttribute('contenteditable');
            editDiv.style.display = 'none';
            frame.style.display = 'block';
            
            if (overrideHtml) {
                frame.removeAttribute('src');
                frame.srcdoc = overrideHtml;
            } else {
                frame.removeAttribute('srcdoc');
                frame.src = currentContentUrl;
            }
            
            document.getElementById('content-edit-btn').style.display = 'inline-block';
            document.getElementById('content-save-btn').style.display = 'none';
            document.getElementById('content-cancel-btn').style.display = 'none';
        }

        function toggleEditMode() {
            isEditMode = !isEditMode;
            updateEditButtons();
        }

        function updateEditButtons() {
            document.querySelectorAll('.delete-checkbox').forEach(cb => cb.style.display = isEditMode ? 'inline-block' : 'none');
            document.getElementById('delete-btn').style.display = isEditMode ? 'inline-block' : 'none';
            document.getElementById('edit-btn').innerText = isEditMode ? '편집 완료' : '목록 편집';
        }

        async function deleteSelected() {
            const checked = document.querySelectorAll('.delete-checkbox:checked');
            document.getElementById('sync-status').innerText = "☁️ 클라우드 동기화 중...";
            
            if (currentView === 'blogs') {
                for (let cb of checked) {
                    dbData.deleted_blogs[cb.value] = true;
                    await updateFirebase(`deleted_blogs/${cb.value}`, true);
                }
                isEditMode = false;
                renderBlogList();
            } else if (currentView === 'posts' && currentBlogId) {
                if (!dbData.deleted_posts[currentBlogId]) dbData.deleted_posts[currentBlogId] = {};
                for (let cb of checked) {
                    dbData.deleted_posts[currentBlogId][cb.value] = true;
                    await updateFirebase(`deleted_posts/${currentBlogId}/${cb.value}`, true);
                }
                isEditMode = false;
                renderPostList(currentBlogId);
            }
            
            document.getElementById('header-bar').style.display = 'none';
            document.getElementById('content-frame').style.display = 'none';
            document.getElementById('content-edit').style.display = 'none';
            document.getElementById('sync-status').innerText = "✅ 동기화 완료";
        }

        function goBackToBlogs() { renderBlogList(); }
    </script>
</body>
</html>"""


def run_all_in_one():
    print("=" * 60)
    print(" 🚀 올인원 단어장 스크래퍼 (네이버 + 티스토리 지원)")
    print("=" * 60)
    
    # 필수 폴더 생성
    if not os.path.exists("id"): os.makedirs("id")
    if not os.path.exists("source"): os.makedirs("source")
    
    # 1. index.html 무조건 최신 템플릿으로 생성 (안의 데이터는 없음, 오직 뼈대)
    output_html_file = "index.html"
    html_content = STATIC_INDEX_HTML.replace("__FIREBASE_DB_URL__", FIREBASE_DB_URL)
    with open(output_html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # 2. 기존 생성된 ID 목록 읽어오기 (_id_list.js 기반 분석이 아니라 파일시스템 직접 확인)
    existing_blog_ids = []
    for filename in os.listdir("id"):
        if filename.endswith(".js") and filename != "_id_list.js":
            existing_blog_ids.append(filename.replace(".js", ""))

    # 3. URL 분석 (호스트네임을 보고 네이버/티스토리 자동 감지)
    full_url = input("\n수집할 카테고리(또는 블로그)의 전체 주소를 붙여넣어 주세요 (네이버 블로그 / 티스토리):\n입력: ").strip()
    parsed_url = urlparse(full_url)
    query_params = parse_qs(parsed_url.query)
    hostname = parsed_url.hostname or ""

    platform = 'tistory' if 'tistory.com' in hostname else 'naver'
    headers = {"User-Agent": "Mozilla/5.0"}

    if platform == 'naver':
        if 'blogId' not in query_params:
            print("\n[오류] 주소에서 'blogId'를 찾을 수 없습니다.")
            sys.exit()

        blog_id = query_params['blogId'][0]
        category_no = query_params['categoryNo'][0] if 'categoryNo' in query_params else ""
        parent_category_no = query_params['parentCategoryNo'][0] if 'parentCategoryNo' in query_params else ""
        blog_url_field = f"https://blog.naver.com/{blog_id}"

        # 4. 목록 추출
        print(f"\n[1단계] '{blog_id}' 블로그 데이터 탐색 중...")
        page = 1
        previous_log_nos = set()
        all_extracted_urls = []
        
        while True:
            target_url = f"https://blog.naver.com/PostList.naver?blogId={blog_id}&currentPage={page}"
            if category_no: target_url += f"&categoryNo={category_no}"
            if parent_category_no: target_url += f"&parentCategoryNo={parent_category_no}"
            
            response = requests.get(target_url, headers=headers)
            response.raise_for_status()
            
            pattern = r'(?:/' + blog_id + r'/|post-view|logNo=)(\d{10,15})'
            found_numbers = re.findall(pattern, response.text)
            current_log_nos = set(found_numbers)
            
            if not current_log_nos or current_log_nos == previous_log_nos:
                break
                
            base_post_url = f"https://blog.naver.com/{blog_id}"
            for log_no in current_log_nos:
                url = f"{base_post_url}/{log_no}"
                if url not in all_extracted_urls:
                    all_extracted_urls.append(url)
            
            print(f"  - {page}페이지 완료 (누적: {len(all_extracted_urls)}개)")
            previous_log_nos = current_log_nos
            page += 1
            time.sleep(0.5)

        if not all_extracted_urls:
            print("\n[알림] 수집할 게시물이 없습니다.")
            sys.exit()

    else:  # platform == 'tistory'
        blog_id = hostname.split('.')[0]  # 서브도메인을 블로그ID로 사용 (예: squiggles)
        raw_path = parsed_url.path
        if raw_path.startswith('/category/'):
            category_no = unquote(raw_path[len('/category/'):]).strip('/')
        else:
            category_no = ""  # 카테고리 없이 통째로 넘기면 블로그 전체 글
        parent_category_no = ""  # 티스토리는 상위 카테고리 개념을 쓰지 않음 (네이버 호환용 빈 값)
        blog_url_field = f"https://{blog_id}.tistory.com"

        # 4. 목록 추출 (티스토리는 카테고리 페이지를 page=1,2,3...으로 직접 순회)
        print(f"\n[1단계] '{blog_id}' 티스토리 블로그 데이터 탐색 중...")
        page = 1
        previous_post_ids = set()
        all_extracted_urls = []

        # 기존 page= 파라미터가 있었다면 제거하고 새로 붙입니다.
        base_url_no_page = re.sub(r'[?&]page=\d+', '', full_url)

        while True:
            sep = '&' if '?' in base_url_no_page else '?'
            page_url = f"{base_url_no_page}{sep}page={page}"

            response = requests.get(page_url, headers=headers)
            response.raise_for_status()
            page_soup = BeautifulSoup(response.text, 'html.parser')

            # ⚠️ 목록 글만 모으고 "최근글/인기글/최근댓글" 같은 사이드바 위젯은 제외해야 합니다.
            #    스킨마다 마크업이 달라 100% 보장은 어렵지만, 페이지네이션의 "다음" 링크나
            #    "분류 전체보기"(카테고리 위젯) 링크가 나오는 지점을 경계로 그 이전 글만 채택합니다.
            all_a_tags = page_soup.find_all('a', href=True)
            cutoff = len(all_a_tags)
            for i, a in enumerate(all_a_tags):
                href = a['href']
                text = a.get_text(strip=True)
                if text == '다음' or re.match(r'^(?:https?://[^/]+)?/category/?$', href):
                    cutoff = i
                    break
            relevant_tags = all_a_tags[:cutoff]

            post_pattern = re.compile(r'^(?:https?://' + re.escape(blog_id) + r'\.tistory\.com)?/(\d+)/?$')
            current_post_ids = set()
            for a in relevant_tags:
                m = post_pattern.match(a['href'])
                if m:
                    current_post_ids.add(m.group(1))

            if not current_post_ids or current_post_ids == previous_post_ids:
                break

            for pid in current_post_ids:
                url = f"https://{blog_id}.tistory.com/{pid}"
                if url not in all_extracted_urls:
                    all_extracted_urls.append(url)

            print(f"  - {page}페이지 완료 (누적: {len(all_extracted_urls)}개)")
            previous_post_ids = current_post_ids
            page += 1
            time.sleep(0.5)

        if not all_extracted_urls:
            print("\n[알림] 수집할 게시물이 없습니다.")
            sys.exit()

    # 5. 고유 ID 부여 및 데이터 병합 결정
    final_blog_folder_id = None

    # 기존 id 폴더 내 파일들을 스캔하여 동일한 데이터가 있는지 확인 (platform + blogUrl + 카테고리로 매칭)
    for e_id in existing_blog_ids:
        js_path = os.path.join("id", f"{e_id}.js")
        if os.path.exists(js_path):
            with open(js_path, 'r', encoding='utf-8') as f:
                content = f.read()
                match_platform = re.search(r'"platform":\s*"([^"]*)"', content)
                match_url = re.search(r'"blogUrl":\s*"([^"]+)"', content)
                match_cat = re.search(r'"categoryNo":\s*"([^"]*)"', content)
                match_pcat = re.search(r'"parentCategoryNo":\s*"([^"]*)"', content)

                # 구버전 파일(platform 필드 없음)은 네이버 전용이었으므로 기본값 naver로 간주
                saved_platform = match_platform.group(1) if match_platform else "naver"

                if match_url:
                    saved_blog_url = match_url.group(1)
                    saved_cat = match_cat.group(1) if match_cat else ""
                    saved_pcat = match_pcat.group(1) if match_pcat else ""

                    if (saved_platform == platform and saved_blog_url == blog_url_field
                            and saved_cat == category_no and saved_pcat == parent_category_no):
                        final_blog_folder_id = e_id
                        break

    if final_blog_folder_id:
        print(f"\n[알림] 기존 목록 '{final_blog_folder_id}'에 데이터를 업데이트 합니다.")
        display_name = final_blog_folder_id
    else:
        # 블로그ID는 같으나 카테고리가 다른 경우 숫자 붙이기
        existing_same_blog = [eid for eid in existing_blog_ids if eid == blog_id or eid.startswith(blog_id + "_")]
        if not existing_same_blog:
            final_blog_folder_id = blog_id
        else:
            suffix = 1
            final_blog_folder_id = f"{blog_id}_{suffix}"
            while final_blog_folder_id in existing_blog_ids:
                suffix += 1
                final_blog_folder_id = f"{blog_id}_{suffix}"
                
        display_name = final_blog_folder_id

    # 6. 본문 스크랩 (source 폴더에 저장)
    print(f"\n[2단계] HTML 본문 추출 (source 폴더 저장 중)...")
    blog_contents_folder = os.path.join("source", final_blog_folder_id)
    if not os.path.exists(blog_contents_folder): os.makedirs(blog_contents_folder)

    scraped_posts = []

    if platform == 'naver':
        failed_posts = []  # ponytail: 실패한 글만 모아서 한 번에 확인하려고 (디버그용)
        # ponytail: 네이버는 에디터 버전별로 본문 마크업이 다름. 새 포맷 나오면 여기 한 줄만 추가하면 됨.
        naver_content_selectors = ['.se-main-container', '#postViewArea', '.se_component_wrap.sect_dsc']
        for index, url in enumerate(all_extracted_urls):
            try:
                log_no = url.split('/')[-1]
                real_url = f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
                res = requests.get(real_url, headers=headers)
                soup = BeautifulSoup(res.text, 'html.parser')
                title_tag = soup.select_one('title')
                title = (title_tag.get_text(strip=True) if title_tag else f"제목 없음").split(':')[0].strip()
                
                # HTML 특수문자 이스케이프 처리 방지 (JSON용 문자열)
                title = title.replace('"', '\\"').replace('\n', '')

                content_tag = None
                for sel in naver_content_selectors:
                    content_tag = soup.select_one(sel)
                    if content_tag:
                        break
                if content_tag:
                    for video in content_tag.select('[class*="video"], [class*="player"], iframe'): video.decompose()
                    for img in content_tag.find_all('img'):
                        real_src = img.get('data-lazy-src') or img.get('data-src') or img.get('src') or ''
                        if real_src: img['src'] = real_src
                else:
                    # ponytail: 후보 셀렉터 다 못 찾은 글 = 또 다른(아직 못 본) 포맷 → 원본을 따로 저장해 비교용으로 남김
                    os.makedirs("debug_failed", exist_ok=True)
                    with open(os.path.join("debug_failed", f"post_{log_no}.html"), 'w', encoding='utf-8') as df:
                        df.write(res.text)
                    failed_posts.append(f"post_{log_no}")
                    print(f"    ⚠️ 본문 추출 실패 → debug_failed/post_{log_no}.html 저장")

                content_html = str(content_tag) if content_tag else "<p>내용 없음</p>"
                sub_html = f"<!DOCTYPE html><html lang='ko'><head><meta charset='UTF-8'><style>body {{ font-family: sans-serif; padding: 20px; }} img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0; }}</style></head><body>{content_html}</body></html>"

                post_id = f"post_{log_no}"
                with open(os.path.join(blog_contents_folder, f"{post_id}.html"), 'w', encoding='utf-8') as sf: sf.write(sub_html)
                scraped_posts.append({"id": post_id, "title": title, "link": url})
                print(f"  - [{index+1}/{len(all_extracted_urls)}] {title[:18]}...")
            except Exception as e:
                pass

        if failed_posts:
            print(f"\n[알림] 본문 추출 실패 {len(failed_posts)}건 → debug_failed 폴더에 원본 저장됨")

    else:  # platform == 'tistory'
        # ⚠️ 티스토리는 스킨(테마)마다 본문을 감싸는 div 클래스가 달라서 여러 후보를 순서대로 시도합니다.
        #    아래 후보에 없는 스킨이면 본문이 비거나 깨질 수 있으니, 그 경우 선택자를 추가해야 합니다.
        tistory_content_selectors = [
            '.tt_article_useless_p_margin',
            '.article_view',
            '.entry-content',
            '#content .area_view',
            'article .contents_style',
        ]
        for index, url in enumerate(all_extracted_urls):
            try:
                res = requests.get(url, headers=headers)
                soup = BeautifulSoup(res.text, 'html.parser')

                og_title = soup.select_one('meta[property="og:title"]')
                if og_title and og_title.get('content'):
                    title = og_title['content'].strip()
                else:
                    title_tag = soup.select_one('title')
                    title = title_tag.get_text(strip=True) if title_tag else "제목 없음"
                title = title.replace('"', '\\"').replace('\n', '')

                content_tag = None
                for sel in tistory_content_selectors:
                    found = soup.select_one(sel)
                    if found:
                        content_tag = found
                        break

                if content_tag:
                    for junk in content_tag.select('script, ins, iframe, [class*="share"], [class*="comment"]'):
                        junk.decompose()
                    for img in content_tag.find_all('img'):
                        real_src = img.get('data-original') or img.get('data-src') or img.get('src') or ''
                        if real_src: img['src'] = real_src

                content_html = str(content_tag) if content_tag else "<p>내용 없음</p>"
                sub_html = f"<!DOCTYPE html><html lang='ko'><head><meta charset='UTF-8'><style>body {{ font-family: sans-serif; padding: 20px; }} img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0; }}</style></head><body>{content_html}</body></html>"

                post_id = f"post_{url.split('/')[-1]}"
                with open(os.path.join(blog_contents_folder, f"{post_id}.html"), 'w', encoding='utf-8') as sf: sf.write(sub_html)
                scraped_posts.append({"id": post_id, "title": title, "link": url})
                print(f"  - [{index+1}/{len(all_extracted_urls)}] {title[:18]}...")
            except Exception as e:
                pass

    # 7. 개별 JS 파일 (id/[ID].js) 생성 및 업데이트 (한 줄 포맷팅)
    print("\n[3단계] 개별 데이터 파일 병합 중...")
    js_file_path = os.path.join("id", f"{final_blog_folder_id}.js")
    
    existing_push_lines = []
    existing_post_ids = set()
    
    # 기존 파일이 있다면 직접 삭제한(하드 삭제) 라인이 유지되도록 파싱합니다.
    if os.path.exists(js_file_path):
        with open(js_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                if 'blog.posts.push' in line:
                    existing_push_lines.append(line.strip())
                    post_id_match = re.search(r'"id":\s*"([^"]+)"', line)
                    if post_id_match:
                        existing_post_ids.add(post_id_match.group(1))
                        
    # 새로운 글만 추가
    new_push_lines = []
    for post in scraped_posts:
        if post['id'] not in existing_post_ids:
            # 💡 한 줄 포맷팅 핵심 부분입니다.
            line = f'    blog.posts.push({{"id": "{post["id"]}", "title": "{post["title"]}", "link": "{post["link"]}"}});'
            new_push_lines.append(line)

    # 최종 JS 파일 작성
    js_content = f"""window.blogsData = window.blogsData || [];
(function() {{
    let blog = {{
        "id": "{final_blog_folder_id}",
        "name": "{display_name}",
        "platform": "{platform}",
        "blogUrl": "{blog_url_field}",
        "categoryNo": "{category_no}",
        "parentCategoryNo": "{parent_category_no}",
        "posts": []
    }};
"""
    for line in existing_push_lines: js_content += f"    {line}\n"
    for line in new_push_lines: js_content += f"{line}\n"
    js_content += f"""    window.blogsData.push(blog);
}})();"""

    with open(js_file_path, 'w', encoding='utf-8') as f:
        f.write(js_content)

    # 8. _id_list.js (메뉴판) 파일 업데이트 (폴더를 직접 스캔하여 동기화)
    # 이 로직 덕분에 사용자가 파이썬 실행 전 id 파일을 삭제했다면 리스트에서도 자동으로 빠집니다.
    print("[4단계] 메뉴판(_id_list.js) 최신화 중...")
    final_active_ids = []
    for filename in os.listdir("id"):
        if filename.endswith(".js") and filename != "_id_list.js":
            final_active_ids.append(filename.replace(".js", ""))
            
    with open(os.path.join("id", "_id_list.js"), 'w', encoding='utf-8') as f:
        f.write(f"const activeBlogIds = {json.dumps(final_active_ids, ensure_ascii=False)};")

    print("=" * 60)
    print(f" ✨ 전자동 모듈화 빌드 완료!")
    print(f" 이제 index.html, id 폴더, source 폴더만 깃허브에 올리시면 됩니다.")
    print("=" * 60)
    input("\n엔터를 누르면 종료됩니다...")

if __name__ == "__main__":
    run_all_in_one()
