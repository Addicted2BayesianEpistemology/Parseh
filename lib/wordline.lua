-- The word line, read for the PDF: lib/wordline.py's grammar in Lua.
--
-- Loaded once by lib/frank-preamble.tex with dofile, so it is ordinary Lua:
-- none of the traps of code written inside \directlua (no # doubled, no %
-- taken for a comment, no backslash or brace eaten by TeX first) reach it,
-- and texlua runs it directly against tests/fixtures/wordline.json.
--
--   M.parse(line)      -> { {surface, reading}, ... }   or nil, code, message
--   M.align(fa, words) -> { {text, reading, k}, ... }   or nil, code, message
--   M.tex(fa, line)    -> the \FrankWord calls that set `fa` a word at a time
--   M.trailing(fa)     -> the punctuation that closes `fa`
--   M.aloud(reading, fa)     -> the chunk as the aloud pass reads it
--   M.tex_aloud(reading, fa) -> the same, with the reading in \FrankAloudText
--
-- k is a word's 0-based index, or false for whitespace between two words.
-- Codes are wordline.py's.  The text is drawn from `fa` and only the division
-- and the readings from the line, so a space the text holds is kept though the
-- line cannot spell it.  All three parsers compare code points without
-- normalising them, so a line that differs from its text only in
-- normalisation is refused by the checker before a build ever reaches here.

local M = {}

local SPACE = {}
for _, c in ipairs({9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 0x85, 0xA0, 0x1680,
                    0x2028, 0x2029, 0x202F, 0x205F, 0x3000}) do
  SPACE[c] = true
end
for c = 0x2000, 0x200A do SPACE[c] = true end

local OPEN, CLOSE, FW_OPEN, FW_CLOSE = 40, 41, 0xFF08, 0xFF09

local function codepoints(s)
  local t = {}
  for _, c in utf8.codes(s) do t[#t + 1] = c end
  return t
end

local function text(t, i, j)
  local out = {}
  for k = i or 1, j or #t do out[#out + 1] = utf8.char(t[k]) end
  return table.concat(out)
end

local function fail(code, message)
  error({code = code, message = message}, 0)
end

local function collapse(t)
  local words, cur = {}, {}
  for _, c in ipairs(t) do
    if SPACE[c] then
      if #cur > 0 then words[#words + 1] = text(cur); cur = {} end
    else
      cur[#cur + 1] = c
    end
  end
  if #cur > 0 then words[#words + 1] = text(cur) end
  return table.concat(words, " ")
end

local function parse(line)
  local t = codepoints(line)
  local n = #t
  local words, surf, read = {}, {}, {}
  local state, start, i = 0, 1, 1        -- 0 surface, 1 reading, 2 closed

  local function shown(e)
    return "'" .. text(t, start, e - 1) .. "'"
  end

  local function finish(e)
    if state == 1 then fail("unclosed", shown(e) .. " opens a reading and never closes it") end
    if #surf > 0 then
      local r = collapse(read)
      if state == 2 and r == "" then
        fail("empty_reading", shown(e) .. " has empty parentheses: a word with no reading is written without them")
      end
      local wide = false
      for _, c in ipairs(surf) do if c == FW_OPEN then wide = true end end
      if wide and surf[#surf] == FW_CLOSE and surf[1] ~= FW_OPEN then
        fail("fullwidth", shown(e) .. " puts its reading in the fullwidth parentheses; a reading is written in ASCII ( )")
      end
      if surf[#surf] == OPEN or r:sub(1, 1) == "(" then
        fail("unwritable", shown(e) .. " ends in a literal (, which cannot be written back")
      end
      words[#words + 1] = {text(surf), r}
    end
    surf, read, state = {}, {}, 0
  end

  while i <= n do
    local c = t[i]
    if state == 2 then
      if not SPACE[c] then
        fail("joined", "a reading ends its word: a space is missing after " .. shown(i))
      end
      finish(i); i = i + 1; start = i
    elseif (c == OPEN or c == CLOSE) and t[i + 1] == c then
      if state == 1 then read[#read + 1] = c else surf[#surf + 1] = c end
      i = i + 2
    elseif state == 0 and SPACE[c] then
      finish(i); i = i + 1; start = i
    else
      if c == OPEN then
        if state == 1 then fail("second_open", "a second ( inside " .. shown(n + 1)) end
        if #surf == 0 then fail("no_word", "a reading with no word in front of it in " .. shown(n + 1)) end
        state = 1
      elseif c == CLOSE then
        if state == 0 then fail("stray_close", "a ) that closes nothing in " .. shown(n + 1)) end
        state = 2
      elseif state == 1 then
        read[#read + 1] = c
      else
        surf[#surf + 1] = c
      end
      i = i + 1
    end
  end
  finish(n + 1)
  return words
end

local function align(fa, words)
  local t = codepoints(fa)
  local n, i, out = #t, 1, {}
  local function mismatch()
    fail("reproduce", "the words do not reproduce the text '" .. fa .. "'")
  end
  for k, w in ipairs(words) do
    local j = i
    while j <= n and SPACE[t[j]] do j = j + 1 end
    if j > i then out[#out + 1] = {text(t, i, j - 1), "", false} end
    i = j
    local start = i
    for _, ch in utf8.codes(w[1]) do
      while i <= n and SPACE[t[i]] do i = i + 1 end
      if i > n or t[i] ~= ch then mismatch() end
      i = i + 1
    end
    out[#out + 1] = {text(t, start, i - 1), w[2], k - 1}
  end
  for k = i, n do
    if not SPACE[t[k]] then mismatch() end
  end
  if i <= n then out[#out + 1] = {text(t, i, n), "", false} end
  return out
end

local function guarded(f)
  return function(...)
    local ok, res = pcall(f, ...)
    if ok then return res end
    if type(res) == "table" then return nil, res.code, res.message end
    error(res, 0)
  end
end

M.parse = guarded(parse)
M.align = guarded(align)

-- The punctuation a chunk's text may close with: wordline.py's TRAIL, range
-- for range.  Declared before M.tex, which is the first to ask: a local
-- function is only in scope below its own line.
local TRAIL = {{0x21, 0x2F}, {0x3A, 0x40}, {0x5B, 0x60}, {0x7B, 0x7E}, {0xA1, 0xBF},
               {0x2010, 0x2027}, {0x2030, 0x205E}, {0x3001, 0x3003}, {0x3008, 0x3011},
               {0x3014, 0x301F}, {0x30FB, 0x30FB}, {0xFF01, 0xFF0F}, {0xFF1A, 0xFF20},
               {0xFF3B, 0xFF40}, {0xFF5B, 0xFF65}}

local function trails(c)
  if not c then return false end
  for _, r in ipairs(TRAIL) do
    if c >= r[1] and c <= r[2] then return true end
  end
  return false
end

-- What opens: a word ending in one of these is not parted from the next.
local OPENS = {}
for _, c in ipairs({0x28, 0x5B, 0x7B, 0xAB, 0x2018, 0x201C, 0x3008, 0x300A, 0x300C,
                    0x300E, 0x3010, 0x3014, 0x3016, 0x3018, 0x301A, 0x301D, 0xFF08,
                    0xFF3B, 0xFF5B, 0xFF5F, 0xFF62}) do
  OPENS[c] = true
end

-- The chunk's text as the calls that set it a word at a time: one
-- \FrankWord{text}{reading} per word, \FrankWordSep between them, and
-- whitespace from the text passed through as a space.  The backslash and the
-- braces are built from their codes, the way frank_breaks builds its
-- \allowbreak, so the answer is the same whatever reads this file.  A line
-- that does not fit the text is a TeX error that names the chunk: the build
-- stops rather than print a reading over the wrong characters.
-- No \FrankWordSep before a word that opens with closing punctuation (、 。 」),
-- nor after one that ends with an opening bracket: a word with its ruby is a
-- box, and the break the separator offers beside it is the one place a line
-- could begin with 。 -- it did, in the fixture edition, the moment 行きました
-- filled a line.  Without it babel keeps the two together as it keeps any two
-- characters its line-breaking rules forbid parting.
-- What may hang past the end of a line (burasagari): the comma and the full
-- stop, ideographic and fullwidth, and nothing else -- a bracket never hangs.
local HANG = {[0x3001] = true, [0x3002] = true, [0xFF0C] = true, [0xFF0E] = true}

function M.tex(fa, line)
  local bs, ob, cb = string.char(92), string.char(123), string.char(125)
  local words, code, message = M.parse(line)
  local spans
  if words then spans, code, message = M.align(fa, words) end
  if not spans then
    tex.error("the word line of the chunk '" .. fa .. "' cannot be set (" .. code .. "): " .. message)
    return fa
  end
  -- A bracket that opens and the marks that close ride with their word.  「 and
  -- 、 。 」 are words of their own in the line, but a line may neither open on
  -- 。 nor end on 「, so each is set inside the word beside it, as
  -- \FrankWordP{opening}{text}{reading}{closing}{hanging}, which measures them
  -- together (the preamble says why: a long word and its comma ran past the
  -- chunk column into the gloss).  {hanging} is a last 、 or 。 alone, the one mark the
  -- preamble may hang past the edge.  A word with neither is \FrankWord.
  local function every(t, test)
    if #t == 0 then return false end
    for _, c in ipairs(t) do if not test(c) then return false end end
    return true
  end
  local function opener(c) return OPENS[c] or false end
  local function closer(c) return trails(c) and not OPENS[c] end
  local items, pre = {}, nil
  local function flush_pre()
    if pre then items[#items + 1] = {pre = "", text = pre, reading = "", post = ""} end
    pre = nil
  end
  for _, s in ipairs(spans) do
    if s[3] == false then
      flush_pre()
      items[#items + 1] = " "
    else
      local t, bare = codepoints(s[1]), s[2] == ""
      if bare and every(t, closer) then
        flush_pre()
        local last = items[#items]
        if type(last) == "table" then
          last.post = last.post .. s[1]
        else
          items[#items + 1] = {pre = "", text = s[1], reading = "", post = ""}
        end
      elseif bare and every(t, opener) then
        pre = (pre or "") .. s[1]
      else
        items[#items + 1] = {pre = pre or "", text = s[1], reading = s[2], post = ""}
        pre = nil
      end
    end
  end
  flush_pre()
  local out, held = {}, false
  for _, it in ipairs(items) do
    if it == " " then
      out[#out + 1] = " "
    else
      local t = codepoints(it.pre .. it.text)
      if #out > 0 and out[#out] ~= " " and not held and not closer(t[1]) then
        out[#out + 1] = bs .. "FrankWordSep "
      end
      if it.pre == "" and it.post == "" then
        out[#out + 1] = bs .. "FrankWord" .. ob .. it.text .. cb .. ob .. it.reading .. cb
      else
        local p = codepoints(it.post)
        local k = #p
        if k > 0 and HANG[p[k]] then k = k - 1 end   -- one mark hangs, never two
        out[#out + 1] = bs .. "FrankWordP" .. ob .. it.pre .. cb .. ob .. it.text .. cb
                        .. ob .. it.reading .. cb .. ob .. text(p, 1, k) .. cb
                        .. ob .. text(p, k + 1) .. cb
      end
      local u = codepoints(it.text .. it.post)
      held = opener(u[#u])
    end
  end
  return table.concat(out)
end

-- The chunk read aloud: wordline.py's trailing() and aloud(), on the same
-- code points (TRAIL, above).  Whitespace inside the closing run is skipped,
-- and a reading that already ends with some of the run gets only the rest.
function M.trailing(fa)
  local t, out = codepoints(fa or ""), {}
  for i = #t, 1, -1 do
    if not SPACE[t[i]] then
      if not trails(t[i]) then break end
      table.insert(out, 1, t[i])
    end
  end
  return text(out)
end

-- (reading, the punctuation it lacks), or nil when there is no reading
local function aloud_parts(reading, fa)
  local r = codepoints(reading or "")
  local i, j = 1, #r
  while i <= j and SPACE[r[i]] do i = i + 1 end
  while j >= i and SPACE[r[j]] do j = j - 1 end
  if i > j then return nil end
  local p = codepoints(M.trailing(fa))
  local k = math.min(#p, j - i + 1)
  while k > 0 do
    local ends = true
    for m = 1, k do
      if r[j - k + m] ~= p[m] then ends = false; break end
    end
    if ends then break end
    k = k - 1
  end
  return text(r, i, j), text(p, k + 1, #p)
end

function M.aloud(reading, fa)
  local r, tail = aloud_parts(reading, fa)
  if not r then return fa or "" end
  return r .. tail
end

-- For \FrankAloud in the preamble: the reading goes into \FrankAloudText, the
-- language's wrapper (Chinese sets its pinyin in the roman), and the text's
-- punctuation stays outside it, in the language's own face.  That punctuation
-- is TeX source cut from the end of the text's, so it is written as what TeX
-- would PRINT: a character TeX reads as syntax becomes \char, and a closing }
-- or % cannot unbalance the pass; an escaped one, 50\% or \#, is the one
-- character it stands for, not a backslash and a percent; any other control
-- symbol (\, a thin space, \ a space) prints no character and is left out,
-- as ~, a space, is.  A chunk with no reading is its text, as \Strip prints it.
local SYNTAX = {[35] = true, [36] = true, [37] = true, [38] = true, [94] = true,
                [95] = true, [123] = true, [125] = true}           -- # $ % & ^ _ { }
local ESCAPED = {[35] = true, [36] = true, [37] = true, [38] = true,
                 [95] = true, [123] = true, [125] = true}          -- \# \$ \% \& \_ \{ \}

function M.tex_aloud(reading, fa)
  local bs, ob, cb = string.char(92), string.char(123), string.char(125)
  local r, tail = aloud_parts(reading, fa)
  if not r then return fa or "" end
  local out, t, i = {bs .. "FrankAloudText" .. ob .. r .. cb}, codepoints(tail), 1
  while i <= #t do
    local c, n = t[i], t[i + 1]
    if c == 92 then
      if n and ESCAPED[n] then out[#out + 1] = bs .. "char" .. n .. " " end
      -- \X with X ASCII is one control symbol; a backslash before anything
      -- else stood before the space the closing run skipped
      i = i + ((n and n < 128) and 2 or 1)
    else
      if SYNTAX[c] then
        out[#out + 1] = bs .. "char" .. c .. " "
      elseif c ~= 126 then
        out[#out + 1] = utf8.char(c)
      end
      i = i + 1
    end
  end
  return table.concat(out)
end

return M
