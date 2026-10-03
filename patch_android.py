# Dijalankan di GitHub Actions setelah `npx cap add android`.
# Menambah ikon dinamis (activity-alias) + kode native kecil + ikon per ekspresi maskot.
import os, re
from PIL import Image

ROOT = "android/app/src/main"
RES = ROOT + "/res"
JAVA = ROOT + "/java/com/remindgo/app"
os.makedirs(JAVA, exist_ok=True)

# alias Icon0..Icon24 = tile 0..24 di icons.png (Icon0 = ikon utama)
COUNT = 25

# ---------- 1. Gambar ikon per ekspresi ----------
from make_assets import tile, bgcolor, square, foreground

FG = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}
LEG = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
os.makedirs(RES + "/mipmap-anydpi-v26", exist_ok=True)
colors = ['<?xml version="1.0" encoding="utf-8"?>', "<resources>"]
for idx in range(1, COUNT):
    n = "t%d" % idx
    im = tile(idx)
    bg = bgcolor(im)
    colors.append('    <color name="ic_%s_bg">#%02X%02X%02X</color>' % ((n,) + bg))
    for d, px in FG.items():
        os.makedirs(RES + "/mipmap-" + d, exist_ok=True)
        foreground(im, px).save("%s/mipmap-%s/ic_%s_fg.png" % (RES, d, n))
    for d, px in LEG.items():
        square(im, px).save("%s/mipmap-%s/ic_%s.png" % (RES, d, n))
    with open("%s/mipmap-anydpi-v26/ic_%s.xml" % (RES, n), "w") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n'
                '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
                '    <background android:drawable="@color/ic_%s_bg"/>\n'
                '    <foreground android:drawable="@mipmap/ic_%s_fg"/>\n'
                '</adaptive-icon>\n' % (n, n))
colors.append("</resources>")
with open(RES + "/values/remind_icon_colors.xml", "w") as f:
    f.write("\n".join(colors) + "\n")

# ---------- 2. Manifest ----------
mp = ROOT + "/AndroidManifest.xml"
s = open(mp, encoding="utf-8").read()
launcher = re.compile(r'\s*<intent-filter>\s*<action android:name="android.intent.action.MAIN"\s*/>\s*'
                      r'<category android:name="android.intent.category.LAUNCHER"\s*/>\s*</intent-filter>')
assert launcher.search(s), "intent-filter LAUNCHER tidak ditemukan"
s = launcher.sub("", s, count=1)

def alias(name, icon, round_icon=""):
    return ('        <activity-alias\n'
            '            android:name=".Icon%s"\n'
            '            android:targetActivity=".MainActivity"\n'
            '            android:enabled="%s"\n'
            '            android:exported="true"\n'
            '            android:icon="@mipmap/%s"\n'
            '%s'
            '            android:label="@string/app_name">\n'
            '            <intent-filter>\n'
            '                <action android:name="android.intent.action.MAIN" />\n'
            '                <category android:name="android.intent.category.LAUNCHER" />\n'
            '            </intent-filter>\n'
            '        </activity-alias>\n') % (name, "true" if name == "0" else "false", icon, round_icon)

block = alias("0", "ic_launcher", '            android:roundIcon="@mipmap/ic_launcher_round"\n')
for idx in range(1, COUNT):
    block += alias(str(idx), "ic_t%d" % idx)
block += ('        <receiver android:name=".IconAlarmReceiver" android:exported="false">\n'
          '            <intent-filter>\n'
          '                <action android:name="android.intent.action.BOOT_COMPLETED" />\n'
          '            </intent-filter>\n'
          '        </receiver>\n')
assert "</application>" in s
s = s.replace("</application>", block + "    </application>", 1)
open(mp, "w", encoding="utf-8").write(s)

# ---------- 3. Kode native ----------
open(JAVA + "/MainActivity.java", "w").write('''package com.remindgo.app;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(AppIconPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
''')

open(JAVA + "/IconSwitcher.java", "w").write('''package com.remindgo.app;

import android.content.ComponentName;
import android.content.Context;
import android.content.pm.PackageManager;

public class IconSwitcher {
    static final String[] NAMES = new String[25];
    static { for (int i = 0; i < 25; i++) NAMES[i] = String.valueOf(i); }

    static ComponentName comp(Context c, String n) {
        return new ComponentName(c.getPackageName(), "com.remindgo.app.Icon" + n);
    }

    static String current(Context c) {
        PackageManager pm = c.getPackageManager();
        for (String n : NAMES) {
            int s = pm.getComponentEnabledSetting(comp(c, n));
            if (s == PackageManager.COMPONENT_ENABLED_STATE_ENABLED
                    || (s == PackageManager.COMPONENT_ENABLED_STATE_DEFAULT && n.equals("0"))) {
                return n;
            }
        }
        return "0";
    }

    static void set(Context c, String name) {
        boolean ok = false;
        for (String n : NAMES) if (n.equals(name)) ok = true;
        if (!ok || current(c).equals(name)) return;
        PackageManager pm = c.getPackageManager();
        // aktifkan yang baru dulu, baru matikan yang lain (supaya selalu ada ikon launcher)
        pm.setComponentEnabledSetting(comp(c, name), PackageManager.COMPONENT_ENABLED_STATE_ENABLED, PackageManager.DONT_KILL_APP);
        for (String n : NAMES) {
            if (!n.equals(name)) {
                pm.setComponentEnabledSetting(comp(c, n), PackageManager.COMPONENT_ENABLED_STATE_DISABLED, PackageManager.DONT_KILL_APP);
            }
        }
    }
}
''')

open(JAVA + "/IconPlan.java", "w").write('''package com.remindgo.app;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import org.json.JSONArray;
import org.json.JSONObject;

public class IconPlan {
    static PendingIntent pi(Context c, int i, String name) {
        Intent it = new Intent(c, IconAlarmReceiver.class);
        if (name != null) it.putExtra("name", name);
        return PendingIntent.getBroadcast(c, 7000 + i, it, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    // json: [{"at": ms, "name": "Kaget"}, ...] urut waktu
    static void apply(Context c, String json) {
        try {
            JSONArray ev = new JSONArray(json);
            AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
            SharedPreferences sp = c.getSharedPreferences("icon_plan", Context.MODE_PRIVATE);
            int old = sp.getInt("n", 0);
            for (int i = 0; i < old; i++) am.cancel(pi(c, i, null));
            long now = System.currentTimeMillis();
            int n = 0;
            String past = null;
            for (int i = 0; i < ev.length() && n < 40; i++) {
                JSONObject o = ev.getJSONObject(i);
                long at = o.getLong("at");
                String name = o.getString("name");
                if (at <= now) { past = name; continue; }
                boolean exact = Build.VERSION.SDK_INT < 31 || am.canScheduleExactAlarms();
                if (exact) am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi(c, n, name));
                else am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi(c, n, name));
                n++;
            }
            sp.edit().putInt("n", n).putString("events", json).apply();
            if (past != null) IconSwitcher.set(c, past);
        } catch (Exception e) {
            // abaikan: ikon dinamis hanya bonus
        }
    }
}
''')

open(JAVA + "/IconAlarmReceiver.java", "w").write('''package com.remindgo.app;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public class IconAlarmReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context c, Intent i) {
        if (Intent.ACTION_BOOT_COMPLETED.equals(i.getAction())) {
            String j = c.getSharedPreferences("icon_plan", Context.MODE_PRIVATE).getString("events", null);
            if (j != null) IconPlan.apply(c, j);
            return;
        }
        String n = i.getStringExtra("name");
        if (n != null) IconSwitcher.set(c, n);
    }
}
''')

open(JAVA + "/AppIconPlugin.java", "w").write('''package com.remindgo.app;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "AppIcon")
public class AppIconPlugin extends Plugin {
    @PluginMethod
    public void setIcon(PluginCall call) {
        String name = call.getString("name", "0");
        IconSwitcher.set(getContext(), name);
        JSObject r = new JSObject();
        r.put("name", IconSwitcher.current(getContext()));
        call.resolve(r);
    }

    @PluginMethod
    public void plan(PluginCall call) {
        JSArray ev = call.getArray("events");
        IconPlan.apply(getContext(), ev == null ? "[]" : ev.toString());
        call.resolve();
    }
}
''')
print("patch_android selesai")
