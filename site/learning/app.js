function populateSelect(select, options) {
  for (const option of options) {
    const el = document.createElement("option");
    el.value = option;
    el.textContent = option;
    select.appendChild(el);
  }
}

function itemMatches(item, typeFilter, formatFilter, difficultyFilter) {
  return (
    (!typeFilter || item.type === typeFilter) &&
    (!formatFilter || item.format === formatFilter) &&
    (!difficultyFilter || item.difficultyLevel === difficultyFilter)
  );
}

function renderSections(filteredItems) {
  const container = document.getElementById("sections");
  container.innerHTML = "";

  for (const sectionTitle of SECTIONS) {
    const sectionItems = filteredItems.filter((item) => item.section === sectionTitle);
    if (sectionItems.length === 0) continue;

    const section = document.createElement("section");
    const heading = document.createElement("h2");
    heading.textContent = sectionTitle;
    section.appendChild(heading);

    const subsections = [...new Set(sectionItems.map((item) => item.subsection).filter(Boolean))];
    const withoutSubsection = sectionItems.filter((item) => !item.subsection);

    for (const item of withoutSubsection) {
      section.appendChild(renderItem(item));
    }

    for (const subsectionTitle of subsections) {
      const subHeading = document.createElement("h3");
      subHeading.textContent = subsectionTitle;
      section.appendChild(subHeading);
      for (const item of sectionItems.filter((item) => item.subsection === subsectionTitle)) {
        section.appendChild(renderItem(item));
      }
    }

    container.appendChild(section);
  }
}

function renderItem(item) {
  const div = document.createElement("div");
  div.className = "item";
  const link = document.createElement("a");
  link.className = "chip";
  link.href = item.url;
  link.textContent = item.name;
  div.appendChild(link);
  return div;
}

function applyFilters() {
  const typeFilter = document.getElementById("filter-type").value;
  const formatFilter = document.getElementById("filter-format").value;
  const difficultyFilter = document.getElementById("filter-difficulty").value;
  const filtered = ITEMS.filter((item) =>
    itemMatches(item, typeFilter, formatFilter, difficultyFilter)
  );
  renderSections(filtered);
}

populateSelect(document.getElementById("filter-type"), TYPES);
populateSelect(document.getElementById("filter-format"), FORMATS);
populateSelect(document.getElementById("filter-difficulty"), DIFFICULTY_LEVELS);

for (const id of ["filter-type", "filter-format", "filter-difficulty"]) {
  document.getElementById(id).addEventListener("change", applyFilters);
}

renderSections(ITEMS);
