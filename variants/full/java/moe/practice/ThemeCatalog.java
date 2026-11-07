package moe.practice;
import org.json.*;
import java.util.*;

/** Theme is an asset redirect. Catalog fields remain the user's own data. */
final class ThemeCatalog {
    static final String[] KEYS={"bg","bg_inverse","bgOverride","track"};
    static JSONObject copy(JSONObject o)throws JSONException{return new JSONObject(o.toString());}
    static Map<String,JSONObject> songs(JSONObject o)throws JSONException {
        Map<String,JSONObject> result=new HashMap<>();JSONArray a=o==null?null:o.optJSONArray("songs");
        if(a!=null)for(int i=0;i<a.length();i++){JSONObject s=a.getJSONObject(i);result.put(s.getString("id"),s);}return result;
    }
    static Map<Integer,JSONObject> difficulties(JSONObject song)throws JSONException {
        Map<Integer,JSONObject> result=new HashMap<>();JSONArray a=song==null?null:song.optJSONArray("difficulties");
        if(a!=null)for(int i=0;i<a.length();i++){JSONObject d=a.getJSONObject(i);result.put(d.optInt("ratingClass",i),d);}return result;
    }
    static boolean same(JSONObject a,JSONObject b,String k){return a.has(k)==b.has(k)&&Objects.equals(a.opt(k),b.opt(k));}
    static void field(JSONObject to,JSONObject from,String k)throws JSONException {if(from.has(k))to.put(k,from.get(k));else to.remove(k);}
    static boolean forced(JSONObject s){return s!=null&&s.optString("bg").equals("finale_conflict")&&s.optString("bg_inverse").equals("finale_conflict")&&s.optString("bgOverride").equals("finale_conflict")&&s.optString("track").equals("dark_vs");}
    private static void mergeFields(JSONObject fresh,JSONObject original,JSONObject last)throws JSONException {
        if(original==null||last==null)return;
        for(String k:KEYS)if(same(fresh,last,k))field(fresh,original,k);
    }
    // Three-way merge by stable identity; additions, deletions, ordering and all
    // non-theme edits come from the user's current songlist, never array index.
    static JSONObject merge(JSONObject incoming,JSONObject catalog,JSONObject last)throws JSONException {
        JSONObject result=copy(incoming);Map<String,JSONObject> originals=songs(catalog),projected=songs(last);
        for(Map.Entry<String,JSONObject> e:songs(result).entrySet()){
            JSONObject orig=originals.get(e.getKey()),prev=projected.get(e.getKey()),fresh=e.getValue();mergeFields(fresh,orig,prev);
            Map<Integer,JSONObject> od=difficulties(orig),pd=difficulties(prev);
            for(Map.Entry<Integer,JSONObject> d:difficulties(fresh).entrySet())mergeFields(d.getValue(),od.get(d.getKey()),pd.get(d.getKey()));
        }return result;
    }
    private static int recoverFields(JSONObject damaged,JSONObject trusted)throws JSONException {
        if(!forced(damaged)||trusted==null||forced(trusted))return 0;
        for(String k:KEYS)field(damaged,trusted,k);return 1;
    }
    // Only repair the exact four-field footprint of the old projection. A
    // bundled baseline is limited to theme metadata, never replaces song data.
    static int recover(JSONObject catalog,JSONObject trusted)throws JSONException {
        int count=0;Map<String,JSONObject> clean=songs(trusted);
        for(Map.Entry<String,JSONObject> e:songs(catalog).entrySet()){
            JSONObject s=e.getValue(),t=clean.get(e.getKey());count+=recoverFields(s,t);
            Map<Integer,JSONObject> td=difficulties(t);
            for(Map.Entry<Integer,JSONObject> d:difficulties(s).entrySet())count+=recoverFields(d.getValue(),td.get(d.getKey()));
        }return count;
    }
}
