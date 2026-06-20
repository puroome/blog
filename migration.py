import os
import re
import json

def migrate_old_data():
    print("=" * 60)
    print(" 🛠️ 기존 단어장 데이터 구조 분리 (마이그레이션) 시작")
    print("=" * 60)

    html_file = "naver_blog.html"
    if not os.path.exists(html_file):
        print(f"[오류] 현재 폴더에 '{html_file}' 파일이 없습니다.")
        return

    # 1. learning_contents 폴더를 source 폴더로 이름 변경
    if os.path.exists("learning_contents"):
        if not os.path.exists("source"):
            os.rename("learning_contents", "source")
            print("✅ 'learning_contents' 폴더 이름을 'source'로 자동 변경했습니다.")
        else:
            print("⚠️ 'source' 폴더가 이미 존재합니다. 내부 파일들을 확인해 주세요.")
    else:
        if not os.path.exists("source"):
            os.makedirs("source")
            print("✅ 'source' 폴더를 새로 생성했습니다.")

    # 2. id 폴더 생성
    if not os.path.exists("id"):
        os.makedirs("id")
        print("✅ 'id' 폴더를 생성했습니다.")

    # 3. 기존 HTML에서 데이터 추출
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()

    match = re.search(r'const blogsData = (\[.*?\]);', content, re.DOTALL)
    if not match:
        print("[오류] HTML 파일에서 기존 블로그 데이터를 찾을 수 없습니다.")
        return

    blogs_data = json.loads(match.group(1))
    extracted_ids = []

    print("\n[작업 시작] 개별 JS 파일로 쪼개는 중...")
    
    # 4. 개별 ID.js 파일 생성 (새로운 1줄 포맷 적용)
    for blog in blogs_data:
        blog_id = blog.get('id')
        if not blog_id: continue

        extracted_ids.append(blog_id)
        js_path = os.path.join("id", f"{blog_id}.js")

        name = blog.get('name', '')
        blog_url = blog.get('blogUrl', '')
        cat_no = blog.get('categoryNo', '')
        pcat_no = blog.get('parentCategoryNo', '')

        js_content = f"""window.blogsData = window.blogsData || [];
(function() {{
    let blog = {{
        "id": "{blog_id}",
        "name": "{name}",
        "blogUrl": "{blog_url}",
        "categoryNo": "{cat_no}",
        "parentCategoryNo": "{pcat_no}",
        "posts": []
    }};
"""
        # 글 목록을 1줄씩 분리해서 저장 (나중에 라인 삭제를 위해)
        for post in blog.get('posts', []):
            p_id = post.get('id', '')
            p_title = post.get('title', '').replace('"', '\\"').replace('\n', '')
            p_link = post.get('link', '')
            js_content += f'    blog.posts.push({{"id": "{p_id}", "title": "{p_title}", "link": "{p_link}"}});\n'

        js_content += f"""    window.blogsData.push(blog);
}})();"""

        with open(js_path, 'w', encoding='utf-8') as f:
            f.write(js_content)
        print(f"  - '{js_path}' 생성 완료 (글 {len(blog.get('posts', []))}개)")

    # 5. _id_list.js (메뉴판) 파일 생성
    id_list_path = os.path.join("id", "_id_list.js")
    with open(id_list_path, 'w', encoding='utf-8') as f:
        f.write(f"const activeBlogIds = {json.dumps(extracted_ids, ensure_ascii=False)};")
    print(f"  - '{id_list_path}' (메뉴판 파일) 생성 완료")

    print("\n" + "=" * 60)
    print(" 🎉 모든 작업이 완벽하게 끝났습니다!")
    print(" 1. 기존 'naver_blog.html'은 이제 지우셔도 됩니다.")
    print(" 2. 이전에 제가 짜드린 새 '올인원 스크래퍼'를 실행하면,")
    print("    분리된 파일들과 완벽하게 연동되어 새 정적 index.html이 생성됩니다.")
    print("=" * 60)

if __name__ == "__main__":
    migrate_old_data()
