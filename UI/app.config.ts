import { _colors, _fontFamily } from "#tailwind-config/theme.mjs";

export default defineAppConfig({
  naiveui: {
    themeConfig: {
      shared: {
        common: {
          fontFamily: _fontFamily.sans.join(", "),
        },
      },
      light: {
        common: {
          primaryColor: _colors.blue[600],
          primaryColorHover: _colors.blue[500],
          primaryColorPressed: _colors.blue[700],
        },
      },
      dark: {
        common: {
          primaryColor: _colors.blue[500],
          primaryColorHover: _colors.blue[400],
          primaryColorPressed: _colors.blue[600],
        },
      },
    },
  },
});
