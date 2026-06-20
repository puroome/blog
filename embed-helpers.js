// 본문 HTML 문자열을 받아 화면 표시 직전에 한 번 가공하는 순수 함수들.
// index.html에서 <script src="embed-helpers.js">로 불러와 사용합니다.
//
// ponytail: 둘 다 정규식 기반 치환이라 다음 한계가 있습니다.
//   - embedYoutube: <a href="..."> 태그로 감싸인 링크만 잡습니다. 태그 없이
//     텍스트로만 적힌 URL은 못 잡음 -> 필요해지면 텍스트 노드까지 훑는 버전으로 업그레이드.
//   - restoreGifLinks: data-linkdata 안에 <img>가 이미 채워진 블록(정상 이미지)은
//     건드리지 않고, 비어있는 블록만 복구합니다.

function embedYoutube(html) {
    return html.replace(
        /<a[^>]*href="https?:\/\/(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)[^"]*"[^>]*>[\s\S]*?<\/a>/g,
        '<div style="position:relative; width:100%; max-width:560px; aspect-ratio:16/9; margin:10px 0;">' +
        '<iframe src="https://www.youtube.com/embed/$1" frameborder="0" allowfullscreen ' +
        'style="position:absolute; top:0; left:0; width:100%; height:100%;"></iframe></div>'
    );
}

function restoreGifLinks(html) {
    return html.replace(
        /<a[^>]*class="[^"]*se-module-image-link[^"]*"[^>]*data-linkdata=(['"])([\s\S]*?)\1[^>]*>\s*<\/a>/g,
        function (match, quote, rawJson) {
            try {
                var jsonStr = rawJson.replace(/&quot;/g, '"').replace(/&amp;/g, '&');
                var data = JSON.parse(jsonStr);
                if (!data.src) return match;
                // 일반 이미지처럼 ?type=w773을 붙여 CDN에 큰 원본을 요청 (작은 기본 버전이 늘어나 깨지는 것 방지)
                // ponytail: 이미 쿼리스트링이 붙어있으면 건드리지 않음
                var src = data.src.indexOf('?') === -1 ? data.src + '?type=w773' : data.src;
                return '<img src="' + src + '" style="max-width:100%; height:auto;">';
            } catch (e) {
                return match; // JSON 파싱 실패하면 원본 그대로 둠 (깨진 화면보단 안전)
            }
        }
    );
}

// ponytail: referer 헤더를 없애는 방식이라, referer 기반 차단에만 효과가 있습니다.
// 그래도 막히면 토큰/서명 기반 차단 등 더 강한 방식이라 클라이언트 단에서 우회 불가 -> 서버 프록시 필요.
function addNoReferrer(html) {
    return html.replace(/<img(?![^>]*\breferrerpolicy=)([^>]*)>/g, '<img referrerpolicy="no-referrer"$1>');
}

// 네이버가 영상 자리를 잡으려고 만든 빈 플레이스홀더(se-module-oembed, padding-top만 있고 내용 없음) 제거.
// 실제 영상은 embedYoutube가 위쪽 <a> 자리에 이미 살려놨으므로 이 빈 박스는 휑한 공간만 만든다.
// ponytail: 내부가 빈(<div ...></div>) 경우만 제거. 내용이 든 oembed는 건드리지 않음.
function removeEmptyOembed(html) {
    return html.replace(/<div[^>]*class="[^"]*se-module-oembed[^"]*"[^>]*>\s*<\/div>/g, '');
}

// Node에서 테스트할 때만 export, 브라우저에서는 그냥 전역 함수로 사용
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { embedYoutube, restoreGifLinks, addNoReferrer, removeEmptyOembed };
}
