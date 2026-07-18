-- Lua filter to render publication links with icons on individual pages

function Meta(meta)
  if meta.links then
    -- Build the links HTML
    local links_html = '<div class="publication-links" style="margin-top: -0.5em; margin-bottom: 1.5em;">'
    
    for _, link in ipairs(meta.links) do
      if link.href and link.text then
        links_html = links_html .. '\n  <a href="' .. pandoc.utils.stringify(link.href) .. '" target="_blank">'
        
        -- Add icon if specified
        if link.icon then
          links_html = links_html .. '<i class="bi bi-' .. pandoc.utils.stringify(link.icon) .. '"></i> '
        end
        
        links_html = links_html .. pandoc.utils.stringify(link.text) .. '</a>'
      end
    end
    
    links_html = links_html .. '\n</div>'
    
    -- Add to the include-before body
    if not meta['include-before'] then
      meta['include-before'] = pandoc.List()
    end
    
    meta['include-before']:insert(pandoc.RawBlock('html', links_html))
  end
  
  return meta
end

-- Read the DOI field out of a per-paper bib file produced by
-- scripts/split_bib.py at pre-render time.
local function lookup_doi(bibkey)
  local paths = {
    'bib/' .. bibkey .. '.bib',
    '../../bib/' .. bibkey .. '.bib',
    '../bib/' .. bibkey .. '.bib',
  }
  if quarto and quarto.project and quarto.project.directory then
    table.insert(paths, 1, quarto.project.directory .. '/bib/' .. bibkey .. '.bib')
  end
  for _, p in ipairs(paths) do
    local f = io.open(p, 'r')
    if f then
      local content = f:read('*all')
      f:close()
      local doi = content:match('doi%s*=%s*{([^}]+)}')
      if doi then return doi end
    end
  end
  return nil
end

local function has_permalink(links)
  if not links then return false end
  for _, link in ipairs(links) do
    if link.text and pandoc.utils.stringify(link.text) == 'Permalink' then
      return true
    end
  end
  return false
end

function Pandoc(doc)
  local meta = doc.meta
  local has_links = meta.links ~= nil
  local has_bibkey = meta.bibkey ~= nil
  local has_venue = meta['container-title'] ~= nil

  if not has_links and not has_bibkey and not has_venue then
    return doc
  end

  local blocks = {}

  if has_venue then
    local venue = pandoc.utils.stringify(meta['container-title'])
    local suffix = ''
    if meta.year then
      suffix = ', ' .. pandoc.utils.stringify(meta.year)
    end
    local venue_html = '<div class="publication-venue">In <em>' .. venue .. '</em>' .. suffix .. '.</div>'
    table.insert(blocks, pandoc.RawBlock('html', venue_html))
  end

  if has_links or has_bibkey then
    local links_html = '<div class="publication-links">'

    if has_links then
      for _, link in ipairs(meta.links) do
        if link.href and link.text then
          links_html = links_html .. '\n  <a href="' .. pandoc.utils.stringify(link.href) .. '" target="_blank">'
          if link.icon then
            links_html = links_html .. '<i class="bi bi-' .. pandoc.utils.stringify(link.icon) .. '"></i> '
          end
          links_html = links_html .. pandoc.utils.stringify(link.text) .. '</a>'
        end
      end
    end

    if has_bibkey then
      local key = pandoc.utils.stringify(meta.bibkey)
      -- Use the DOI as a Permalink fallback when the page doesn't already
      -- declare an explicit Permalink (avoids duplicating dl.acm.org/doi/<doi>
      -- links that resolve to the same content as doi.org/<doi>).
      if not has_permalink(meta.links) then
        local doi = lookup_doi(key)
        if doi then
          links_html = links_html .. '\n  <a href="https://doi.org/' .. doi .. '" target="_blank">'
          links_html = links_html .. '<i class="bi bi-link"></i> Permalink</a>'
        end
      end
      links_html = links_html .. '\n  <a href="/bib/' .. key .. '.bib" download="' .. key .. '.bib">'
      links_html = links_html .. '<i class="bi bi-braces"></i> BibTeX</a>'
    end

    links_html = links_html .. '\n</div>'
    table.insert(blocks, pandoc.RawBlock('html', links_html))
  end

  for i = #blocks, 1, -1 do
    table.insert(doc.blocks, 1, blocks[i])
  end
  return doc
end

return {{Pandoc = Pandoc}}