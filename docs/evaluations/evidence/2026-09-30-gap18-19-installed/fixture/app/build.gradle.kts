plugins { id("com.android.application") }
dependencies {
  implementation(project(":identity"))
  implementation(project(":external"))
  add("${flavor}Implementation", project(":debugkit"))
}
