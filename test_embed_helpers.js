const assert = require('assert');
const { embedYoutube, restoreGifLinks, addNoReferrer, removeEmptyOembed } = require('./embed-helpers.js');

// 일반 유튜브 링크 -> 임베드 치환 (16:9 비율 컨테이너 + embed URL)
const ytOut = embedYoutube('<a href="https://www.youtube.com/watch?v=sq-fDVl7yZo">https://www.youtube.com/watch?v=sq-fDVl7yZo</a>');
assert(ytOut.includes('src="https://www.youtube.com/embed/sq-fDVl7yZo"'), '유튜브(watch?v=) 임베드 치환 실패');
assert(ytOut.includes('aspect-ratio:16/9'), '16:9 비율 컨테이너가 적용되지 않음');
assert(!ytOut.includes('height="315"'), '고정 height가 남아있음 (제거되어야 함)');

// youtu.be 단축 링크도 처리되는지 확인
const ytShortOut = embedYoutube('<a href="https://youtu.be/abc123XYZ">link</a>');
assert(ytShortOut.includes('embed/abc123XYZ'), 'youtu.be 단축링크 처리 실패');

// 빈 GIF 링크(실제 스크랩 샘플과 동일한 구조, 싱글쿼트 원본 그대로) 복구 확인 + 큰 원본 요청 파라미터 확인
const gifIn = '<a class="se-module-image-link __se_image_link __se_link" data-linkdata=\'{"id" : "x", "src" : "https://postfiles.pstatic.net/test/2.gif", "originalWidth" : "540", "originalHeight" : "300", "linkUse" : "false", "link" : ""}\' data-linktype="img" href="#" onclick="return false;" style="">\n</a>';
const gifOut = restoreGifLinks(gifIn);
assert(gifOut.includes('src="https://postfiles.pstatic.net/test/2.gif?type=w773"'), 'GIF 복구/큰원본 파라미터 적용 실패');
assert(!gifOut.includes('width="540"'), 'width 강제 속성이 남아있음 (제거되어야 함)');

// iframe.contentDocument.innerHTML을 한 번 거치면 브라우저가 더블쿼트+&quot;로 재조립함 -> 이 형태도 잡혀야 함
const gifInEscaped = '<a class="se-module-image-link __se_image_link __se_link" data-linkdata="{&quot;id&quot; : &quot;x&quot;, &quot;src&quot; : &quot;https://postfiles.pstatic.net/test/2.gif&quot;, &quot;originalWidth&quot; : &quot;540&quot;}" data-linktype="img" href="#" onclick="return false;" style="">\n</a>';
const gifOutEscaped = restoreGifLinks(gifInEscaped);
assert(gifOutEscaped.includes('src="https://postfiles.pstatic.net/test/2.gif?type=w773"'), 'GIF 복구 실패 (브라우저가 재조립한 더블쿼트+escape 형태)');

// 이미 img가 채워진 정상 이미지 블록은 그대로 보존되는지 확인 (회귀 방지)
const normalImg = '<a class="se-module-image-link"><img src="https://postfiles.pstatic.net/test/1.jpg"></a>';
assert.strictEqual(restoreGifLinks(normalImg), normalImg, '정상 이미지 블록이 잘못 변경됨');

console.log('모든 테스트 통과 ✅');

// 일반 img에 referrerpolicy 부여되는지 확인
const plainImg = '<img src="https://postfiles.pstatic.net/test/1.jpg" alt="">';
assert(addNoReferrer(plainImg).includes('referrerpolicy="no-referrer"'), 'referrerpolicy 부여 실패');

// 이미 referrerpolicy가 있으면 중복으로 또 안 붙이는지 확인
const alreadySet = '<img referrerpolicy="origin" src="x.jpg">';
assert.strictEqual(addNoReferrer(alreadySet), alreadySet, '이미 설정된 referrerpolicy를 덮어씀');

console.log('addNoReferrer 테스트 통과 ✅');

// 영상 자리의 빈 oembed 플레이스홀더(개발자도구에서 확인된 실제 구조) 제거 확인
const emptyOembed = '<div class="se-module se-module-oembed se-is-progress" style="padding-top: 56.25%;"></div>';
assert.strictEqual(removeEmptyOembed(emptyOembed), '', '빈 oembed 플레이스홀더 제거 실패');

// 내용이 든 oembed는 건드리지 않는지 확인 (회귀 방지)
const filledOembed = '<div class="se-module se-module-oembed"><iframe src="x"></iframe></div>';
assert.strictEqual(removeEmptyOembed(filledOembed), filledOembed, '내용 있는 oembed가 잘못 제거됨');

console.log('removeEmptyOembed 테스트 통과 ✅');
