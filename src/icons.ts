import { LabIcon } from '@jupyterlab/ui-components';

const claudeSpark = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16">
  <path d="M12 1.5C12 6.5 14 9 19 9.5C14 10 12 12.5 12 17.5C12 12.5 10 10 5 9.5C10 9 12 6.5 12 1.5Z" fill="#4361ee"/>
  <path d="M18.5 14C18.5 16 19.5 17 21.5 17.25C19.5 17.5 18.5 18.5 18.5 20.5C18.5 18.5 17.5 17.5 15.5 17.25C17.5 17 18.5 16 18.5 14Z" fill="#4361ee"/>
</svg>
`;

export const claudeIcon = new LabIcon({
  name: 'jclaude:claude-icon',
  svgstr: claudeSpark.trim()
});
