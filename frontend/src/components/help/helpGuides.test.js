import { HELP_GUIDES, HELP_MANUAL_URL, getHelpGuidePdfUrl } from './helpGuides';

describe('help guides', () => {
  it('keeps both contextual guides on the bundled PDF manual', () => {
    expect(HELP_MANUAL_URL).toBe('/manuals/budezivo-odkazy-a-comgate.pdf');
    expect(getHelpGuidePdfUrl(HELP_GUIDES['web-links'])).toBe(`${HELP_MANUAL_URL}#page=3`);
    expect(getHelpGuidePdfUrl(HELP_GUIDES.comgate)).toBe(`${HELP_MANUAL_URL}#page=6`);
  });

  it('marks Comgate as optional instead of a required setup step', () => {
    expect(HELP_GUIDES.comgate.optional).toBe(true);
    expect(HELP_GUIDES['web-links'].optional).toBeUndefined();
  });
});
