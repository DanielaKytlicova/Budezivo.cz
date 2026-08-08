const DEFAULT_PRIMARY_COLOR = '#192938';

const escapeHtml = (value) => String(value ?? '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#039;');

const textToHtml = (value) => escapeHtml(value).replace(/\r?\n/g, '<br/>');

export const buildProgramBookingUrl = (institutionId, programId) => {
  if (!institutionId || !programId) return null;
  return `https://www.budezivo.cz/booking/${encodeURIComponent(institutionId)}?program=${encodeURIComponent(programId)}`;
};

const targetGroupLabels = {
  ms_3_6: 'MŠ',
  zs1_7_12: '1. stupeň ZŠ',
  zs2_12_15: '2. stupeň ZŠ',
  ss_14_18: 'SŠ',
  gym_14_18: 'Gymnázium',
  adults: 'Dospělí',
  all: 'Všechny skupiny',
};

const renderProgramCard = (program, institutionId, primaryColor) => {
  const name = escapeHtml(program.name_cs || program.name || 'Program');
  const description = escapeHtml(String(program.description_cs || program.description || '').slice(0, 200));
  const duration = program.duration ? `${escapeHtml(program.duration)} min` : '';
  const groups = (program.target_groups || []).map(group => targetGroupLabels[group] || group).join(', ');
  const bookingUrl = buildProgramBookingUrl(institutionId, program.id);

  const inner = `
    <h3 style="margin:0 0 4px;color:${primaryColor};font-size:16px">${name}</h3>
    ${description ? `<p style="color:#475569;font-size:14px;margin:4px 0 8px">${description}</p>` : ''}
    <div style="color:#64748b;font-size:13px">
      ${duration ? `<span>${duration}</span>` : ''}
      ${duration && groups ? '<span style="margin:0 8px">·</span>' : ''}
      ${groups ? `<span>${escapeHtml(groups)}</span>` : ''}
    </div>
    ${bookingUrl ? `<div style="margin-top:12px;color:${primaryColor};font-size:14px;font-weight:700">Vybrat termín →</div>` : ''}
  `;

  const cardStyle = 'display:block;text-decoration:none;color:inherit;border:1px solid #e2e8f0;border-radius:8px;padding:16px;margin:12px 0;background:#fafbfc';
  return bookingUrl
    ? `<a href="${escapeHtml(bookingUrl)}" target="_blank" rel="noopener noreferrer" style="${cardStyle}">${inner}</a>`
    : `<div style="${cardStyle}">${inner}</div>`;
};

export const buildCampaignPreviewHtml = ({
  greeting,
  introText,
  programs,
  closingText,
  signature,
  institutionId,
  institutionName,
  primaryColor = DEFAULT_PRIMARY_COLOR,
}) => {
  const safeColor = /^#[0-9a-f]{6}$/i.test(primaryColor) ? primaryColor : DEFAULT_PRIMARY_COLOR;
  const bookingUrl = institutionId
    ? `https://www.budezivo.cz/booking/${encodeURIComponent(institutionId)}`
    : null;

  return `
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:600px;margin:0 auto;background:#fff">
      <div style="background:${safeColor};padding:24px;border-radius:8px 8px 0 0">
        <h1 style="color:#fff;margin:0;font-size:20px">${escapeHtml(institutionName || 'Vaše instituce')}</h1>
      </div>
      <div style="padding:24px">
        <p style="color:#334155;font-size:15px;line-height:1.6">${textToHtml(greeting)}</p>
        <p style="color:#475569;font-size:15px;line-height:1.6">${textToHtml(introText)}</p>
        <div style="margin:24px 0">${(programs || []).map(program => renderProgramCard(program, institutionId, safeColor)).join('')}</div>
        ${bookingUrl ? `
          <div style="text-align:center;margin:24px 0">
            <a href="${escapeHtml(bookingUrl)}" target="_blank" rel="noopener noreferrer" style="display:inline-block;background:${safeColor};color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-size:15px;font-weight:500">Zobrazit termíny a rezervovat</a>
          </div>` : ''}
        <p style="color:#475569;font-size:15px;line-height:1.6">${textToHtml(closingText)}</p>
        <p style="color:#64748b;font-size:14px;line-height:1.6;margin-top:24px">${textToHtml(signature)}</p>
      </div>
    </div>`;
};
